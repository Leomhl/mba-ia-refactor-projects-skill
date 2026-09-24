```
==================================
ARCHITECTURE AUDIT REPORT
==================================
Project: ecommerce-api-legacy
Stack:   Node.js 22 + Express 4.18.2
Files:   3 analyzed | ~180 lines of code
Date:    2026-09-21
```

## Summary

CRITICAL: 5 | HIGH: 6 | MEDIUM: 5 | LOW: 3

## Deprecated APIs

| API | Occurrences | Replacement | Severity |
|---|---|---|---|
| `require('sqlite3').verbose()` | 1 (`src/AppManager.js:1`) | driver without `.verbose()` outside development | MEDIUM |
| `substring()` over a Buffer result | 2 (`src/utils.js:20,22`) | `slice()` | LOW |

`.verbose()` attaches the full JavaScript stack trace to driver errors. Since
the handlers pass `err` back to the client in several places, this becomes a
server file path leak.

## Findings

### [CRITICAL] Hardcoded production credentials (AP-01)

**File:** `src/utils.js:2-6`

**Description:** The `config` object carries four literal secrets: database
user and password (`admin_master` / `senha_super_secreta_prod_123`), the
payment gateway key with a production prefix (`pk_live_1234567890abcdef`) and
the SMTP user. The `_prod_` infix in the password name indicates these are
production credentials, not samples.

**Impact:** The `pk_live_` key allows operating the payment gateway on the
company's behalf. Since it is versioned, it has already leaked to every clone
of the repository — removing it at HEAD does not help, the value must be
rotated at the provider.

**Recommendation:** Move to environment variables with an `.env.example`
publishing only the key names, and rotate all four secrets (playbook RP-01).

### [CRITICAL] Hand-rolled password hashing (AP-06)

**File:** `src/utils.js:17-23`, `src/AppManager.js:18`, `src/AppManager.js:68`

**Description:** The `badCrypto` function (lines 17-23) runs 10,000
iterations concatenating the first two characters of the password's Base64
encoding, then returns the first 10 characters of the result. Since each
iteration produces the same character pair, the loop is decorative: the
output is that same pair repeated five times. There is no salt. The seed on
line 18 writes the password `123` in plaintext, without even passing through
that function.

**Impact:** The output depends only on the password's leading bytes, so
`senha123` and `senhaXYZ` collide. The search space is small enough to invert
by table: the "hash" is reversible in practice. Base64 is encoding, not
encryption.

**Recommendation:** Replace with `bcrypt` at cost 12, and re-hash existing
records on the next successful login (playbook RP-12).

### [CRITICAL] Card number and gateway key written to logs (AP-22, AP-05)

**File:** `src/AppManager.js:45`

**Description:** The line logs, via `console.log`, the full card number
received in the request along with the payment gateway key:
`` console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`) ``.

**Impact:** Plaintext card data on stdout is a direct PCI DSS violation, and
stdout is collected by any log aggregator in the environment. An incident in
the logging system becomes a payment data incident.

**Recommendation:** Log only the last four digits, in a structured format,
and never the gateway key (playbook RP-16).

### [CRITICAL] God Class spanning infrastructure, routes and business (AP-04)

**File:** `src/AppManager.js:4-139`

**Description:** `AppManager` opens the database connection in its
constructor (line 7), creates the schema and loads the seed in `initDb`
(10-23), and declares all three routes in `setupRoutes` (25-138) —
implementing inside them the charging rule, user creation, enrollment and the
financial report assembly. The generic name is the symptom: the class has no
definable responsibility.

**Impact:** There is no boundary to test against. Verifying the rule "a card
starting with 4 is approved" requires instantiating the entire class, which
opens a database and registers routes as side effects. Every change, of any
nature, concentrates in a single file.

**Recommendation:** Separate into `config`, `infra` (connection and schema),
`repositories`, `services`, `controllers` and `routes`, with composition done
at the entry point (playbook RP-03 and RP-05).

### [CRITICAL] Administrative and destructive routes without authentication (AP-03)

**File:** `src/AppManager.js:80`, `src/AppManager.js:131`

**Description:** `GET /api/admin/financial-report` returns revenue per course
and the named list of paying students, with amounts paid.
`DELETE /api/users/:id` deletes any user by id. Neither verifies identity,
role or token — there is no authentication middleware in the project.

**Impact:** The report exposes company revenue and students' personal data to
any anonymous request. The delete endpoint allows removing users in a loop,
and the absence of referential integrity (finding below) means each deletion
corrupts the database further.

**Recommendation:** Introduce authentication and role-based authorization
middleware, applied to the `/api/admin` prefix and to destructive
operations.

### [HIGH] Checkout without a transaction: enrollment and payment can diverge (AP-10)

**File:** `src/AppManager.js:50-63`

**Description:** The sequence writes `enrollments` (line 50), then `payments`
(54), then `audit_logs` (57), each in the previous one's callback. There is
no `BEGIN`, `COMMIT` or `ROLLBACK`. Each `if (err) return res.status(500)`
aborts the chain, leaving whatever was already written in the database.

**Impact:** A failure inserting the payment leaves an active enrollment with
no corresponding charge — the student has course access and the company was
not paid. The reverse also happens if the charge is recorded and the audit
write fails. In a financial domain, silent inconsistency is worse than a
visible error.

**Recommendation:** Wrap the three writes in an explicit transaction with
rollback on error (playbook RP-08).

### [HIGH] Delete without referential integrity (AP-11)

**File:** `src/AppManager.js:131-137`, `src/AppManager.js:12-16`

**Description:** The tables are created without a single `FOREIGN KEY` clause
(lines 12-16) and SQLite additionally has checking disabled by default. The
delete handler removes only the `users` row and responds — the message on
line 135 documents the problem itself: *"Usuário deletado, mas as matrículas
e pagamentos ficaram sujos no banco."*

**Impact:** Confirmed at runtime: after `DELETE /api/users/1`, the financial
report starts listing `"student": "Unknown"` with a payment of 997.00
attached to a nonexistent user. Revenue keeps being counted over orphaned
enrollments, so the financial report is permanently incorrect.

**Recommendation:** Declare the foreign keys in the schema, enable
`PRAGMA foreign_keys = ON` per connection, and choose the policy per
relationship — `CASCADE` for enrollments, preservation for payments, which
cannot vanish from the accounting history (playbook RP-09).

### [HIGH] Callback hell with manual flow control (AP-12)

**File:** `src/AppManager.js:83-128`, `src/AppManager.js:37-77`

**Description:** The financial report nests four callback levels and
coordinates completion with two manually decremented counters
(`coursesPending` and `enrPending`, lines 86, 93, 97, 117-121). Checkout uses
the same technique and additionally has to capture `const self = this` (line
26) because `function(err)` loses the lexical `this`.

**Impact:** `res.json(report)` is reachable through two distinct paths (lines
98 and 121). With a course without enrollments processed in parallel with a
course that has them, the counters can reach zero twice and trigger
`ERR_HTTP_HEADERS_SENT`, crashing the process. Query errors at the inner
levels (lines 104 and 106) are simply ignored.

**Recommendation:** Promisify the driver and rewrite with `async/await`,
eliminating the counters (playbook RP-10).

### [HIGH] Mutable global state that does not work (AP-09)

**File:** `src/utils.js:9-10`, `src/utils.js:25`, `src/AppManager.js:59`

**Description:** `globalCache` and `totalRevenue` are mutable module
variables, exported on line 25. `logAndCache` writes to the cache on every
checkout (called at line 59 of `AppManager.js`). Nothing in the project reads
either of them.

**Impact:** Beyond the coupling, there is a silent defect: `totalRevenue` is
a primitive number, and `module.exports` copies the value at require time.
Importers will always see `0`, regardless of updates. The cache grows without
bound or expiry — a memory leak proportional to the number of checkouts,
holding data nobody consumes.

**Recommendation:** Remove both. If the cache is needed later, it becomes an
injected dependency with an expiry policy (playbook RP-05).

### [HIGH] Database connection instantiated inside its consumer (AP-08)

**File:** `src/AppManager.js:7`

**Description:** The constructor runs `new sqlite3.Database(':memory:')`,
pinning both the driver and the destination. There is no way to inject
another connection, and the in-memory database is a code choice, not a
configuration one.

**Impact:** All data disappears on every restart — the seed recreates three
records and the previous payment history is gone. For production that is data
loss; for testing, it prevents using an isolated database per case.

**Recommendation:** Receive the connection as a parameter and create it at
the composition root from configuration (playbook RP-05).

### [HIGH] Payment business rule inside the HTTP handler (AP-07)

**File:** `src/AppManager.js:43-64`

**Description:** The `processPaymentAndEnroll` function is declared inside
the route handler. The charge approval rule is on line 46 as a ternary over
the card's first character (`cc.startsWith("4") ? "PAID" : "DENIED"`),
followed by enrollment creation, payment recording and the audit log.

**Impact:** The business's central rule — when a charge is approved — is not
reachable outside an HTTP request. Replacing the simulation with a real
gateway would require rewriting the entire handler.

**Recommendation:** Extract a `CheckoutService` receiving an injected payment
gateway, and reduce the handler to receive, delegate and respond (playbook
RP-04).

### [MEDIUM] N+1 query in the financial report (AP-13)

**File:** `src/AppManager.js:83-106`

**Description:** The report queries all courses (line 83), then each course's
enrollments (92), then each enrollment's user (104) and payment (106) — four
levels of chained per-item queries.

**Impact:** With 50 courses and 30 enrollments each, the endpoint fires 3,051
queries to build one response. Since they all share the same in-memory SQLite
connection, they serialize and the time grows quadratically.

**Recommendation:** Replace with a single query using `LEFT JOIN` across
`courses`, `enrollments`, `users` and `payments`, grouping in memory
(playbook RP-07).

### [MEDIUM] Ignored errors and contractless responses (AP-15)

**File:** `src/AppManager.js:104`, `src/AppManager.js:106`,
`src/AppManager.js:133`, `src/AppManager.js:38`, `src/AppManager.js:41`

**Description:** The callbacks on lines 104 and 106 receive `err` and never
check it. Line 133 likewise — the delete responds with success even if it
fails. Error responses are plain text (`"Bad Request"`, `"Erro DB"`,
`"Curso não encontrado"`) while success responses are JSON, and line 38
returns 404 both for a nonexistent course and for a database error. No error
middleware is registered.

**Impact:** A database failure during deletion returns 200 to the client,
which assumes success. Clients must handle two body formats depending on the
status. And a 404 masking an infrastructure error prevents diagnosis.

**Recommendation:** Centralize in an `(err, req, res, next)` error middleware
with an exception hierarchy and a uniform JSON body (playbook RP-11).

### [MEDIUM] Superficial input validation (AP-16)

**File:** `src/AppManager.js:29-35`

**Description:** The only validation is the presence of four fields on line
35. There is no type check, email format check, or card format/length check.
The `pwd` field is not even validated — line 68 applies a default of
`"123456"` when it is absent.

**Impact:** A `c_id` arriving as a string or object goes straight into the
query. And silently creating an account with a default password produces
users with predictable credentials, without the owner knowing the account
exists.

**Recommendation:** Validate with a schema at the edge, rejecting the payload
before any database access, and require an explicit password (playbook
RP-13).

### [MEDIUM] Configuration coupled to the code (AP-18)

**File:** `src/utils.js:1-7`, `src/app.js:12`, `src/AppManager.js:7`

**Description:** The `config` object is a source literal. Port 3000 lives in
it, the database destination (`:memory:`) lives in the `AppManager`
constructor, and there is no `.env.example` nor any `process.env` read
anywhere in the project.

**Impact:** No configuration is adjustable per environment: promoting
requires editing and rebuilding the image. It is also the root cause of the
CRITICAL credentials finding — with no environment-reading entry point, the
secrets had nowhere else to go.

**Recommendation:** A configuration module reading `process.env` with safe
defaults, and a versioned `.env.example` (playbook RP-01).

### [MEDIUM] Driver in verbose mode (AP-17)

**File:** `src/AppManager.js:1`

**Description:** `require('sqlite3').verbose()` enables the driver's extended
tracing, which attaches the full JavaScript stack trace to error objects.

**Impact:** Combined with the handlers that pass error information to the
client, it exposes absolute server file paths. The mode also has a measurable
performance cost, since it captures a stack on every operation.

**Recommendation:** Enable `.verbose()` only when configuration indicates a
development environment.

### [LOW] Single-letter naming and abbreviated API contract (AP-21)

**File:** `src/AppManager.js:29-33`, `src/AppManager.js:132`

**Description:** The checkout variables are `u`, `e`, `p`, `cid` and `cc`.
The request body fields — which are a public contract consumed by external
clients — use `usr`, `eml`, `pwd`, `c_id` and `card`.

**Impact:** `e` is especially poor in JavaScript, where convention associates
`e` with event or error; here it is email. Abbreviated contract fields force
every integrator to consult a sample payload to discover that `c_id` is the
course id.

**Recommendation:** Rename the internal variables during Service extraction.
The payload fields remain, being a public contract — changing them would
require API versioning.

### [LOW] Dead code and unused dependency (AP-20)

**File:** `src/utils.js:5`, `src/utils.js:9-15`, `src/utils.js:25`,
`src/AppManager.js:2`

**Description:** `smtpUser` is defined and never used — there is no email
sending in the project. `logAndCache` and `globalCache` write to a cache
nothing reads. `totalRevenue` is imported on line 2 of `AppManager.js` and
never referenced.

**Impact:** It implies features that do not exist. A new developer looks for
where email is sent and where the cache is read, and finds neither.

**Recommendation:** Remove them. Whatever is needed later comes back with a
real implementation.

### [LOW] `console.log` as a logging strategy (AP-22)

**File:** `src/AppManager.js:45`, `src/utils.js:13`, `src/app.js:13`

**Description:** All three occurrences use `console.log` with a template
string, with no severity level and no structured fields. No logging library
is declared in `package.json`.

**Impact:** Impossible to filter by severity or index in production. The
occurrence on line 45 is also the CRITICAL card leak finding — with
structured logging and a field policy, it would not have gone unnoticed.

**Recommendation:** Adopt a logging library with levels and structured
serialization (playbook RP-16).

```
==================================
Total: 19 findings
==================================
```

## Out of scope

1. **In-memory database.** Phase 3 makes the destination configurable, but
   keeping `:memory:` as the default preserves the current behavior of
   booting without external dependencies. Migrating to real persistence is an
   infrastructure decision.

2. **Authentication on administrative routes.** Phase 3 introduces the
   middleware and applies it, but the project has no credential issuance —
   there is no login. The protection implemented is a service token from the
   environment; a full identity scheme requires a product definition.

3. **Renaming the payload fields** (`usr`, `eml`, `c_id`). They are a public
   contract; changing them would break existing clients and require API
   versioning.
