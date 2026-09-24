```
==================================
ARCHITECTURE AUDIT REPORT
==================================
Project: task-manager-api
Stack:   Python 3.12 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
Files:   15 analyzed | ~1,160 lines of code
Date:    2026-09-21
```

## Summary

CRITICAL: 3 | HIGH: 5 | MEDIUM: 5 | LOW: 4

A project with partial layer separation. The directory structure exists
(`models/`, `routes/`, `services/`, `utils/`), which already eliminates much
of what was found in the monolithic projects — there is no concatenated SQL
and no God Module. The findings concentrate on responsibilities leaking
between layers, a missing Controller layer, and deprecated API debt.

## Deprecated APIs

| API | Occurrences | Replacement | Severity |
|---|---|---|---|
| `Query.get()` / legacy Query API | 46 | `db.session.get()` / `db.session.scalars(select(...))` | MEDIUM |
| `datetime.utcnow()` | 18 | `datetime.now(timezone.utc)` | MEDIUM |
| `hashlib.md5` for passwords | 2 | `generate_password_hash` | CRITICAL (see AP-06) |

The first two were confirmed at runtime, not merely by inspection. The
project declares `flask-sqlalchemy 3.1.1`, which installs SQLAlchemy 2.0.54,
and the runtime emits:

```
LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x
series of SQLAlchemy and becomes a legacy construct in 2.0.
```

## Findings

### [CRITICAL] Passwords hashed with unsalted MD5 (AP-06)

**File:** `models/user.py:29`, `models/user.py:32`

**Description:** `set_password` applies `hashlib.md5` to the received value
and stores the hex digest. `check_password` compares the stored hash against
the MD5 of the supplied password. There is no salt, no cost factor, and no
constant-time comparison.

**Impact:** MD5 is designed to be fast — the opposite of what a password
function requires. A commodity GPU computes billions of digests per second,
and without a salt the attack is performed once against the entire database.
The value `81dc9bdb52d04dc20036dbd8313ed055`, present in the sample data,
appears in any public rainbow table: it corresponds to `1234`.

**Recommendation:** Switch to Werkzeug's `generate_password_hash` /
`check_password_hash`, already available as a Flask dependency, with
transparent re-hashing on the next successful login (playbook RP-12).

### [CRITICAL] Password hash exposed in API responses (AP-05)

**File:** `models/user.py:21`, `routes/user_routes.py:33`,
`routes/user_routes.py:85`, `routes/user_routes.py:129`,
`routes/user_routes.py:209`

**Description:** The `User` entity's `to_dict` serializer includes the
`password` field (line 21). Since handlers use it unfiltered, the hash ships
in four endpoints: `GET /users/<id>`, `POST /users`, `PUT /users/<id>` and —
most seriously — in the `POST /login` response.

**Impact:** Confirmed at runtime: `GET /users/1` returns
`"password": "81dc9bdb52d04dc20036dbd8313ed055"`. Combined with the unsalted
MD5 above, publishing the hash is equivalent to publishing the password. Note
that `GET /users` (the listing) builds its dictionary manually and escapes
the problem — which shows that the inconsistency between serializers is also
what masks the leak during a superficial review.

**Recommendation:** Remove `password` from `to_dict` and create a separate
method for internal use where needed (playbook RP-12).

### [CRITICAL] Hardcoded credentials in source (AP-01)

**File:** `app.py:13`, `services/notification_service.py:7-10`

**Description:** `SECRET_KEY` is the literal `'super-secret-key-123'`
(`app.py:13`). `NotificationService` carries host, port, user and SMTP
password fixed in its constructor, including `email_password = 'senha123'`.
The project declares `python-dotenv` in `requirements.txt` but does not use
it anywhere — the intent to read environment variables existed and was never
finished.

**Impact:** The `SECRET_KEY` signs Flask sessions; once known, it allows
forging session cookies. The SMTP credentials allow sending email on behalf
of the application's domain — a direct phishing vector against its own
users.

**Recommendation:** Extract into a configuration module reading environment
variables, publish `.env.example`, and rotate the exposed secrets (playbook
RP-01).

### [HIGH] Missing Controller layer: routes accumulate everything (AP-07)

**File:** `routes/task_routes.py:11-63`, `routes/task_routes.py:85-154`,
`routes/report_routes.py:12-101`, `routes/user_routes.py:42-90`

**Description:** The route files concentrate validation, serialization,
domain rules and aggregation. `get_tasks` (lines 11-63) builds the dictionary
field by field, computes the overdue state and fetches user and category
names. `create_task` (85-154) runs 14 sequential validations before
persisting. `summary_report` (12-101) executes more than twenty queries and
assembles the entire report inside the handler. A `services/` directory
exists, but it contains only `NotificationService`, which nobody calls.

**Impact:** No rule is reusable or testable without booting the HTTP server.
The folder structure suggests a separation the code does not practice — which
is worse than having no structure, because it leads whoever arrives next to
add more logic to the route, following the existing pattern.

**Recommendation:** Introduce `controllers/` and move the rules into
`services/`, leaving the route files as pure declaration. The `routes/`
folder keeps its current name, which is already appropriate (playbook RP-04,
RP-06).

### [HIGH] "Overdue task" rule duplicated in five places (AP-14)

**File:** `models/task.py:50-59`, `routes/task_routes.py:30-39`,
`routes/task_routes.py:71-80`, `routes/user_routes.py:171-180`,
`routes/report_routes.py:34-43`, `routes/report_routes.py:132-135`

**Description:** The definition of an overdue task — has a due date, the date
has passed, and the status is neither `done` nor `cancelled` — is rewritten
six times. The model already exposes `is_overdue()` (lines 50-59) with
exactly that rule, and none of the five handlers uses it: all reimplement the
same triple-nested `if`.

Task serialization has the same problem: `Task.to_dict()` exists
(`models/task.py:23-36`), but `get_tasks` (`task_routes.py:17-28`) and
`get_user_tasks` (`user_routes.py:162-169`) build the dictionary manually,
with different field sets from one another.

**Impact:** Six copies mean six places to update when the definition changes
— for example, when introducing a new status. And the serializations have
already diverged: `GET /users/<id>/tasks` returns neither `tags` nor
`updated_at`, which `GET /tasks` does return. The same resource has different
shapes depending on the access path.

**Recommendation:** Use the model's `is_overdue()` and `to_dict()` everywhere,
extending the serializer with a parameter for derived fields (playbook
RP-13).

### [HIGH] N+1 query in four endpoints (AP-13)

**File:** `routes/task_routes.py:42`, `routes/task_routes.py:51`,
`routes/report_routes.py:56`, `routes/report_routes.py:163`,
`routes/user_routes.py:22`

**Description:** `get_tasks` queries each task's user (line 42) and category
(line 51) individually, inside the loop. `summary_report` fetches each user's
tasks with one query per user (line 56). `get_categories` counts tasks per
category one query at a time (line 163). `get_users` accesses `len(u.tasks)`
(line 22), which triggers lazy loading per user.

**Impact:** `GET /tasks` with 200 tasks emits 401 queries, even though the
`user` and `category` relationships are already declared on the model
(`models/task.py:20-21`) and a `joinedload` would resolve everything. In
`GET /reports/summary`, cost grows with the number of registered users, not
with the report size.

**Recommendation:** Declare eager loading with `joinedload` on task queries,
and replace the counts with `GROUP BY` aggregation (playbook RP-07).

### [HIGH] Predictable authentication token (AP-06)

**File:** `routes/user_routes.py:210`

**Description:** A successful login returns
`'token': 'fake-jwt-token-' + str(user.id)`. The value is derived entirely
from the user id, is not signed, does not expire, and no endpoint verifies
it.

**Impact:** Anyone can generate any user's token by changing the trailing
number. Since no route validates the token, the practical effect today is
nil — but the format leads clients to treat it as a legitimate credential,
and the first route that starts verifying it inherits a complete
authentication failure.

**Recommendation:** Issue a JWT signed with the environment-provided
`SECRET_KEY`, with expiry, or remove the field until authentication is
actually implemented. Since the choice alters the API contract, the decision
is recorded under "Out of scope".

### [HIGH] Dead service coupled to infrastructure (AP-08, AP-20)

**File:** `services/notification_service.py:1-48`

**Description:** `NotificationService` is neither imported nor instantiated
anywhere in the project — 48 lines of dead code. The implementation
instantiates `smtplib.SMTP` directly in `send_email` (line 15), with host,
port and credentials fixed in the constructor. Notification history
accumulates in an instance list (line 6), which would be lost on every
restart.

**Impact:** It is the only class in `services/`, which makes the layer look
present when it is in practice empty. The coupling to `smtplib` would prevent
testing delivery without a real SMTP server, and the synchronous call inside
the request cycle would block the response for the duration of the
handshake.

**Recommendation:** Move the credentials into configuration and inject the
email transport, keeping the class only if it is wired into the task
assignment flow; otherwise delete the file (playbook RP-05).

### [MEDIUM] Deprecated SQLAlchemy 2.0 and Python 3.12 APIs (AP-17)

**File:** `routes/task_routes.py:14`, `routes/task_routes.py:67`,
`routes/task_routes.py:117`, `routes/task_routes.py:158`,
`routes/user_routes.py:29`, `routes/user_routes.py:94`,
`models/task.py:15-16`, `models/task.py:52`, `routes/report_routes.py:35`
(+ 37 more occurrences in the same files)

**Description:** 46 calls use the legacy Query API (`Model.query.get`,
`Model.query.all`, `Model.query.filter_by`) and 18 use `datetime.utcnow()`.
`requirements.txt` pins `flask-sqlalchemy 3.1.1`, which resolves to
SQLAlchemy 2.0.54 — the version where `Query.get()` emits a
`LegacyAPIWarning` at runtime, confirmed during the audit.

**Impact:** `datetime.utcnow()` returns a naive datetime (no timezone). The
`created_at`, `updated_at` and `due_date` columns are written that way, and
the overdue comparisons work only because both sides are equally naive. Any
timezone-aware value entering the system raises
`TypeError: can't compare offset-naive and offset-aware datetimes`. The
legacy SQLAlchemy calls stop working in the next major version.

**Recommendation:** Migrate to `db.session.get()` and
`db.session.scalars(select(...))`, and replace `datetime.utcnow()` with
`datetime.now(timezone.utc)` across all occurrences at once — a partial
migration mixes naive and aware datetimes, which do not compare (playbook
RP-14).

### [MEDIUM] Bare `except` swallowing exceptions (AP-15)

**File:** `routes/task_routes.py:62`, `routes/task_routes.py:137`,
`routes/task_routes.py:204`, `routes/task_routes.py:236`,
`routes/user_routes.py:130`, `routes/user_routes.py:149`,
`routes/report_routes.py:186`, `routes/report_routes.py:207`,
`routes/report_routes.py:221`

**Description:** Nine blocks use a bare `except:`, which catches even
`KeyboardInterrupt` and `SystemExit`. The most severe case is
`task_routes.py:62`: it wraps the entire body of `get_tasks` and returns
`{'error': 'Erro interno'}` for any failure, recording nothing. No global
error handler is registered on the application.

**Impact:** Any defect in `get_tasks` — from a type error to a connection
failure — produces the same generic message, with no stack trace in the log.
Debugging the endpoint in production is impossible: the information was
discarded.

**Recommendation:** Register global handlers with an application exception
hierarchy, and replace the local blocks with typed handling where it still
makes sense (playbook RP-11).

### [MEDIUM] Validation without type checking and listings without pagination (AP-16)

**File:** `routes/task_routes.py:113`, `routes/task_routes.py:182`,
`routes/task_routes.py:261`, `routes/task_routes.py:264`,
`routes/task_routes.py:14`, `routes/user_routes.py:12`,
`routes/report_routes.py:159`

**Description:** The comparisons `priority < 1 or priority > 5` (lines 113
and 182) run without checking the value's type. In `search_tasks`, query
string parameters go straight into `int()` (lines 261 and 264) with no error
handling. None of the listings has pagination: `GET /tasks`, `GET /users`,
`GET /categories` and `GET /tasks/search` return the entire table.

**Impact:** `POST /tasks` with `{"priority": "alta"}` raises `TypeError` and
returns 500, when 400 would be correct — and the exception is swallowed by
the bare `except` above, with no log. `GET /tasks/search?priority=abc` raises
an unhandled `ValueError`. The listings degrade as the database grows.

**Recommendation:** Validate types before comparing, convert query parameters
with explicit error handling, and introduce pagination with a configurable
cap (playbook RP-13).

### [MEDIUM] Configuration coupled and schema created at import time (AP-18)

**File:** `app.py:11-13`, `app.py:15`, `app.py:30-31`, `app.py:34`

**Description:** The database URI, tracking flag and `SECRET_KEY` are
literals (lines 11-13). `CORS(app)` opens any origin (line 15). The
`with app.app_context(): db.create_all()` block runs at module level (30-31),
i.e. on import. `app.run(debug=True)` pins debug mode (line 34). The
`python-dotenv` dependency is declared and unused.

**Impact:** `db.create_all()` at import means that importing `app` — for a
test, for `seed.py`, for an introspection tool — creates a database file as a
side effect. `debug=True` exposes the Werkzeug interactive console, which
executes arbitrary Python on the server.

**Recommendation:** Extract a configuration module reading environment
variables with `python-dotenv` (already declared), and move schema creation
into an application factory or an explicit command (playbook RP-01).

### [MEDIUM] Deleting a category leaves tasks pointing at a nonexistent id (AP-11)

**File:** `routes/report_routes.py:211-223`, `routes/user_routes.py:140-142`,
`models/task.py:13-14`

**Description:** `delete_category` removes the category without checking or
handling the tasks that reference it. The foreign keys are declared on the
model (`models/task.py:13-14`), but without `ondelete` and without a cascade
on the relationship, and SQLite keeps checking disabled by default.
`delete_user` compensates for the gap by deleting tasks manually in a loop
(`user_routes.py:140-142`) — the rule exists, but it lives in the handler
rather than the schema, and only for one of the two relationships.

**Impact:** Confirmed by tracing the flow: after removing a category, tasks
retain a `category_id` pointing at a nonexistent record, and `GET /tasks`
starts returning `category_name: null` silently. The per-category report
stops counting them without signalling the loss.

**Recommendation:** Declare `ondelete` on the foreign keys and the cascade
policy on the relationship, keeping integrity in the schema instead of in
loops scattered across handlers (playbook RP-09).

### [LOW] Constants defined and never imported (AP-19)

**File:** `utils/helpers.py:110-116`, `routes/task_routes.py:110`,
`routes/task_routes.py:177`, `routes/user_routes.py:71`,
`routes/user_routes.py:120`, `models/task.py:39`

**Description:** `utils/helpers.py` defines `VALID_STATUSES`, `VALID_ROLES`,
`MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`,
`DEFAULT_PRIORITY` and `DEFAULT_COLOR` (lines 110-116). None is imported
anywhere. The same lists are retyped in four handlers and in the model.

**Impact:** Adding a new status requires locating five different literals.
The existing constants file gives the false impression that centralization
has already been done.

**Recommendation:** Import the constants at the usage sites and remove the
literal duplicates (playbook RP-15).

### [LOW] Unused imports, functions and dependencies (AP-20)

**File:** `routes/task_routes.py:7`, `app.py:7`, `routes/user_routes.py:6`,
`utils/helpers.py:3-7`, `utils/helpers.py:25-34`, `utils/helpers.py:36-41`,
`utils/helpers.py:57-108`, `requirements.txt:4-6`

**Description:** `task_routes.py` imports `json, os, sys, time` and uses
none. `app.py` imports `os, sys, json, datetime` and uses only `datetime`.
`user_routes.py` imports `hashlib` and `json` without using them. In
`helpers.py`, five of the six imports are unused, and the functions
`sanitize_string`, `generate_id`, `log_action`, `is_valid_color`,
`validate_email` and `process_task_data` (57-108, 52 lines on its own) are
never called — the last one reimplements, for the seventh time, the
validation already in the handlers. `requirements.txt` declares
`marshmallow`, `requests` and `python-dotenv`, none of which is imported in
the project.

**Impact:** `process_task_data` is the costliest: whoever sets out to fix
validation may modify it believing they are changing API behavior, with no
effect at all. Extra declared dependencies widen the security update surface
without delivering function.

**Recommendation:** Remove the dead imports and functions, and align
`requirements.txt` with what is actually imported.

### [LOW] Redundant conditionals (AP-23)

**File:** `models/user.py:34-38`, `models/task.py:38-43`,
`models/task.py:45-48`, `models/task.py:50-59`, `utils/helpers.py:19-23`,
`utils/helpers.py:52-55`

**Description:** The pattern `if condition: return True else: return False`
appears six times — `is_admin` (user.py:34-38) is literally
`return self.role == 'admin'` written across five lines. `is_overdue`
(task.py:50-59) uses three nested `if` levels with `else: return False` at
each level to express a conjunction of three conditions.

**Impact:** Low in itself, but `is_overdue` is precisely the function the
handlers ignored and reimplemented — the nested form makes it harder to
recognize that it does exactly what they needed.

**Recommendation:** Reduce to direct boolean expressions.

### [LOW] Single-letter naming and type checking by comparison (AP-21)

**File:** `routes/task_routes.py:16`, `routes/task_routes.py:141`,
`routes/task_routes.py:210`, `routes/user_routes.py:14`,
`routes/report_routes.py:33`, `routes/report_routes.py:55`,
`routes/report_routes.py:119`, `routes/report_routes.py:161`, `seed.py:79`

**Description:** Loops use `t`, `u`, `c`, `p` and `td` as entity names. Type
checking is done with `type(tags) == list` (`task_routes.py:141` and `210`)
instead of `isinstance`.

**Impact:** `type(x) == list` rejects `list` subclasses and is slower than
`isinstance`. Single-letter names in 40-line loops force the reader back to
the top of the block to recall what is being iterated.

**Recommendation:** Name by entity (`task`, `user`, `category`) and use
`isinstance`.

```
==================================
Total: 17 findings
==================================
```

## Out of scope

1. **Implementing real authentication.** The predictable token at
   `user_routes.py:210` is flagged, but replacing it with a signed JWT
   changes the contract for every client and requires decisions about expiry,
   refresh and protected routes. Phase 3 removes the misleading field only if
   approved; by default it preserves the behavior and documents it.

2. **Removing `NotificationService`.** The class is dead, but it may
   represent planned functionality. Phase 3 fixes the coupling and moves the
   credentials into configuration, without deciding on deletion.

3. **Pagination as the default on listings.** It is introduced with optional
   parameters and a cap, preserving current behavior when the client sends no
   `limit` — making pagination mandatory would break clients that consume the
   full list.
