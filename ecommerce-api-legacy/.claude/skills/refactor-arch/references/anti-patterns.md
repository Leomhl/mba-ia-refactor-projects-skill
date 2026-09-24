# Anti-pattern catalog

Phase 2 knowledge. Each entry carries its detection signal — what to look for
literally in the code — and its base severity.

How to use it: sweep the project once per severity block, starting with the
CRITICAL ones. Look for the signal, not the general impression. "This code
looks bad" is not detection; grepping for concatenation inside `execute(` is.

## Severity scale

| Level | Criterion |
|---|---|
| **CRITICAL** | Serious architectural or security failure that prevents correct operation, exposes sensitive data, or completely violates separation of concerns. |
| **HIGH** | Strong MVC or SOLID violation that severely hinders maintenance and testing. |
| **MEDIUM** | Consistency problem, duplication, or moderate performance bottleneck. |
| **LOW** | Readability, naming, magic numbers. |

The base severity may go up one level when context makes it worse (public
surface, sensitive data, write path) or down when it mitigates (internal
script, isolated dead code). Any level change must be justified in the
finding's `Impact` field.

---

## CRITICAL

### AP-01 — Hardcoded credentials

A literal secret in versioned source code.

**Signals:** assignments containing `SECRET_KEY`, `password`, `passwd`,
`pwd`, `api_key`, `token`, `apiKey`, `dbPass` with a string literal on the
right; keys with recognizable prefixes (`pk_live_`, `sk_`, `AKIA`, `ghp_`,
`xoxb-`); SMTP or database credentials inside a class constructor; a
`config` object with literal values instead of environment reads.

**Why CRITICAL:** the secret leaked the moment it entered Git history.
Removing it at HEAD does not fix it — whoever has the clone has the key.

**Aggravating factor:** a payment gateway key or production credential goes
to the top of the priority list even within CRITICAL itself.

### AP-02 — SQL Injection via concatenation

Untrusted input becoming query text.

**Signals:** `execute(` receiving an expression with `+`, `%`, `.format()`,
an f-string or a template literal; a query built by accumulation
(`query += " AND field = '" + value + "'"`); `LIKE '%" + term + "%'`.

**Contrast with the correct form:** a parameterized query uses placeholders
(`?`, `%s`, `:name`, `$1`) and passes values in a separate list. If the
values are inside the string, it is injection.

**Note:** interpolating an already-validated integer is less severe than
interpolating a raw string from `request`, but both belong in the report —
the first because the validation may disappear in a future refactor, and the
pattern is what propagates.

### AP-03 — Arbitrary execution exposed over HTTP

An endpoint that accepts code or SQL from the client and runs it.

**Signals:** a route reading a field named `sql`, `query`, `cmd`, `code` or
`script` and passing it to `execute`, `eval`, `exec`, `system` or
`Function()`; an unauthenticated administrative route that deletes or resets
data (`/admin/reset-db`, `/admin/query`, `/debug/*`).

**Why CRITICAL:** it is RCE or a full database dump in a single request,
with no exploit needed — the endpoint does the work for you.

### AP-04 — God Class / God Module

One file concentrating domains and layers that should not know each other.

**Signals:** a single file over ~250 lines covering more than one business
domain; a class that opens database connections, declares routes and
implements business rules (look for `class *Manager`, `*Helper`, `*Handler`,
`*Utils` with many heterogeneous methods); a `setupRoutes` method that also
implements what the routes do.

**Impact:** any change touches the file everyone else touches — guaranteed
merge conflicts, impossible isolated testing.

### AP-05 — Sensitive data exposed in responses

Data that should never leave the application appearing in the payload.

**Signals:** a serializer (`to_dict`, `toJSON`, `serialize`) including a
`password`, `hash`, `token`, `ssn` or `card` field; a health or debug
endpoint returning `secret_key`, `db_path` or environment flags; a
`SELECT *` on a users table whose result goes straight into the response.

**Aggravating factor:** if the exposed field is a password hash, add the
algorithm used to the finding — a weak hash exposed is a plaintext
credential given enough GPU time.

### AP-06 — Inadequate password cryptography

Passwords stored in a way that does not survive a database leak.

**Signals:** plaintext passwords in the table; `md5(`, `sha1(`, `sha256(`
applied to passwords without salt; direct comparison
`stored_password == typed_password`; a homemade hash implementation (a loop
concatenating `base64`, XOR, character rotation).

**Why CRITICAL:** MD5 and SHA-1 are fast by design, which is exactly the
opposite of what a password function needs. The correct choice is bcrypt,
scrypt or Argon2 — slow, with a per-record salt.

**Specific signal for homemade hashing:** a function named something like
`badCrypto`, `myHash` or `encrypt` that merely shuffles bytes. Encoding is
not encryption: Base64 is reversible by definition.

---

## HIGH

### AP-07 — Business logic inside the Controller or route

The HTTP handler deciding domain rules.

**Signals:** a handler over ~40 lines; price, discount, tax or commission
calculation inside the handler; an `if` over domain state deciding business
flow; direct database access (`cursor.execute`, `db.run`, `Model.query`)
inside the route function; a side effect (email, SMS, push, audit log)
triggered inline in the handler.

**Rule of thumb:** the Controller receives, delegates and responds. If it
decides *what* the business does — rather than merely *whom* to delegate
to — the logic is in the wrong place.

### AP-08 — Tight coupling without dependency injection

A module instantiating or importing what it depends on concretely.

**Signals:** `new Database()` inside the constructor of its consumer; a
direct import of the connection module in a route file; a global connection
singleton reachable by everyone (`global db_connection`); a
`require`/`import` of a concrete implementation where an abstraction belongs.

**Impact:** there is no seam for testing. Testing the controller requires a
real database running, so nobody tests it.

### AP-09 — Mutable global state

A shared module-level variable anyone can write to.

**Signals:** `global` in Python, module-scope `let` in JS mutated by
functions; a cache in a shared object literal (`globalCache = {}`); a
business-value accumulator in a module variable (`totalRevenue = 0`); a
single connection held in a global.

**Extra trap in JS:** exporting a primitive (`module.exports = {
totalRevenue }`) exports a *copy* of the value. Importers never see updates —
the global state is not just fragile, it silently does not work.

### AP-10 — Multi-step operation without a transaction

A sequence of writes that can stop halfway and leave the database
inconsistent.

**Signals:** two or more related `INSERT`/`UPDATE` statements without an
explicit `BEGIN`/`COMMIT`; stock decrement and order creation in separate
commands; a payment recorded after enrollment with no rollback when the
second step fails; a single `commit` at the end of a block that already
performed conditional reads (check-then-act without a lock — opens a race
window).

**Impact:** negative stock, enrollment without payment, payment without
enrollment. In a financial domain, this rises to CRITICAL.

### AP-11 — Delete without referential integrity

Deleting the parent and leaving the children orphaned.

**Signals:** `DELETE FROM parent` with no `ON DELETE CASCADE` on the FK and
no explicit delete of dependents; a foreign key declared without a real
constraint (`FOREIGN KEY` missing from `CREATE TABLE`); the response message
itself admitting the problem.

**How to confirm:** delete a parent record and query the child table. If the
rows are still there pointing at a nonexistent id, the finding is proven —
and the result is worth citing in the report.

### AP-12 — Callback hell / manual async flow control

Asynchrony coordinated by hand, with counters.

**Signals:** three or more levels of nested callbacks; a manual pending
counter (`let pending = items.length; pending--`) deciding when to respond;
`forEach` with an async operation inside (it awaits nothing); `res.send`
called from within a nested callback on more than one branch — risk of double
response and `ERR_HTTP_HEADERS_SENT`.

**Fix:** promisify and use `async/await` with `Promise.all`. The pattern is
in the playbook.

---

## MEDIUM

### AP-13 — N+1 query

One query for the list, plus one per item in the list.

**Signals:** `execute`/`query`/`Model.query.get` inside a `for`/`forEach`/
`map`; nested query loops (order → items → product of each item); in an ORM,
accessing a relationship attribute inside a loop without a declared `join`
or eager loading.

**How to measure for the report:** estimate the query count for N records.
"1 + N × 2 queries to list N orders" communicates the cost better than
"there's an N+1 here".

### AP-14 — Duplicated logic

The same decision block copied in different places.

**Signals:** identical validation blocks in `create` and `update`; the same
entity-to-dictionary transformation rewritten in every handler instead of
using the model's serializer; the same derived rule (e.g. computing
"overdue") reimplemented in three files.

**Escalate to HIGH when:** the copies have already diverged. Two versions of
the same rule mean one of them is wrong and nobody knows which.

### AP-15 — Error handling missing, generic, or leaking internals

The error that vanishes, or the error that says too much.

**Signals:** `except:` / `catch {}` with no type and no re-raise; `str(e)` or
`e.message` returned in the response body; the same `try/except` block copied
into every handler instead of one global error handler; an async callback
ignoring its `err` parameter; error responses without an appropriate status
code.

**Two faces of the same problem:** swallowing the error hides the bug;
leaking the raw exception hands table structure and file paths to anyone
probing.

### AP-16 — Missing or late input validation

Client data reaching the database without validation.

**Signals:** `request.body`/`get_json()` read and used directly; no type
check before a numeric comparison (`price < 0` explodes if `price` arrives as
a string); a required field with no presence check; validation scattered
across sequential `if`s instead of a schema; missing pagination on a list
endpoint (it is a limit validation nobody wrote).

### AP-17 — Deprecated or obsolete API

Use of an API the ecosystem itself marks as legacy.

**Signals per stack:**

| Deprecated | Modern replacement | Context |
|---|---|---|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12+; returns a naive datetime, a timezone bug source |
| `Model.query.get(id)` | `db.session.get(Model, id)` | SQLAlchemy 2.0 |
| `Model.query` (Query API) | `db.session.execute(select(...))` | SQLAlchemy 2.0 |
| `hashlib.md5` / `sha1` for passwords | `bcrypt`, `argon2` | any version |
| `flask.Markup`, `flask.escape` | `markupsafe.Markup`, `escape` | Flask 2.3+ |
| `@app.before_first_request` | `with app.app_context()` at boot | removed in Flask 2.3 |
| `url_quote` from `werkzeug.urls` | `urllib.parse.quote` | Werkzeug 3.0 |
| `new Buffer(x)` | `Buffer.from(x)` | Node 6+; known vulnerability |
| `require('sqlite3').verbose()` in production | driver without `.verbose()`, or `node:sqlite` | exposes stack traces |
| `util.isArray`, `util._extend` | `Array.isArray`, `Object.assign` | Node 4+ |
| `res.send(status, body)` | `res.status(status).send(body)` | Express 4 |
| `app.del(...)` | `app.delete(...)` | Express 4 |
| `crypto.createCipher` | `crypto.createCipheriv` | Node 10+ |
| `substr()` | `slice()` / `substring()` | JS, deprecated in Annex B |
| `var` | `const` / `let` | ES6 |
| `moment.js` | `date-fns`, `Temporal`, `Intl` | project in maintenance mode |
| `request` (npm) | native `fetch`, `axios`, `undici` | discontinued in 2020 |

**How to check the version:** confirm the version declared in the manifest
before classifying. `datetime.utcnow()` on Python 3.8 is merely dated; on
3.12 it emits a `DeprecationWarning` and has an announced removal. The
version changes the severity.

**Severity:** MEDIUM by default; HIGH when the deprecated API has security
implications (`new Buffer`, `createCipher`, MD5 for passwords) or when it has
already been removed in the version the project declares — at that point it
is not debt, it is an upgrade time bomb.

### AP-18 — Configuration coupled to the code

An environment value hardcoded in source.

**Signals:** host, port, database path or external service URL as a literal;
`debug=True` in production code; CORS opened to any origin (`CORS(app)`
without restriction, `Access-Control-Allow-Origin: *`); no `.env.example` in
a project that clearly needs configuration.

**Practical consequence:** promoting to another environment requires editing
code. A fixed port also breaks local development when another process
already holds it.

---

## LOW

### AP-19 — Magic numbers and magic strings

An unnamed literal scattered through the code.

**Signals:** literal numeric ranges in validation (`if p >= 1 and p <= 5`);
a list of valid values retyped in every file instead of a shared constant;
size limits (`len(name) > 200`) repeated; discount tiers
(`> 10000 → 0.1`) with no rule name.

### AP-20 — Dead code and unused imports

Things that are there and do nothing.

**Signals:** `import os, sys, json, datetime` with half unused; a function
declared and never called; a variable assigned and never read; constants
defined in a module and imported by nobody; a parameter always receiving the
same value.

**Why it matters despite being LOW:** an unused import misleads the reader —
whoever arrives next assumes the module is used and propagates the
confusion.

### AP-21 — Poor and inconsistent naming

A name that does not say what the thing is.

**Signals:** single-letter variables outside a short loop (`u`, `e`, `p`,
`cid`, `cc`); abbreviated API field names (`usr`, `eml`, `pwd`, `c_id`) — a
public contract is documentation; mixed languages within the same project;
`data`, `result`, `temp`, `info` as final names; numbered `cursor2`,
`cursor3`.

### AP-22 — `print`/`console.log` as a logging strategy

Debugging left behind in production.

**Signals:** `print(` or `console.log(` on a request path; logs concatenating
strings instead of structured fields; sensitive data inside the log (card
number, API key, password); no logging library in the manifest at all.

**Escalate to CRITICAL when:** the log prints a credit card or a gateway key.
At that point it is not style, it is a leak — usually recorded alongside
AP-01 or AP-05.

### AP-23 — Redundant conditionals and needless nesting

Structure more complicated than the decision it makes.

**Signals:** `if cond: return True else: return False` (that is
`return cond`); chained `if x: if y: if z:` instead of a guard clause or a
combined condition; `else` after `return`; comparison against a boolean
(`if flag == True`); `if len(list) == 0` instead of `if not list`.

---

## Sweep coverage checklist

Before closing Phase 2, confirm you looked for each group:

- [ ] Secrets and credentials (AP-01)
- [ ] Query construction (AP-02, AP-03)
- [ ] File size and responsibility (AP-04)
- [ ] What goes out in responses (AP-05)
- [ ] Password storage (AP-06)
- [ ] Route handler contents (AP-07)
- [ ] How dependencies are obtained (AP-08, AP-09)
- [ ] Write atomicity and integrity (AP-10, AP-11)
- [ ] Async flow control (AP-12)
- [ ] Queries inside loops (AP-13)
- [ ] Repeated blocks (AP-14)
- [ ] Error paths (AP-15)
- [ ] Unvalidated input and unbounded listings (AP-16)
- [ ] Deprecated APIs against declared versions (AP-17)
- [ ] Configuration fixed in code (AP-18)
- [ ] Literals, dead code, naming, logs, conditionals (AP-19 to AP-23)
