# refactor-arch — Automated architectural refactoring skill

A Claude Code skill that audits a backend project and refactors it to MVC.
Three phases: detect the stack, cross-reference the code against an
anti-pattern catalog and — after human confirmation — restructure the project
and validate that the endpoints still respond.

Built by reading three legacy projects (two Python/Flask, one Node/Express)
and executed on all three without changing its contents.

```
.claude/skills/refactor-arch/
├── SKILL.md                      # phases, rules and exit gates
└── references/
    ├── project-analysis.md       # stack and architecture-level detection
    ├── anti-patterns.md          # 23 anti-patterns + 17 deprecated APIs
    ├── report-template.md        # report format
    ├── mvc-guidelines.md         # layers and dependency direction
    └── refactoring-playbook.md   # 16 before/after transformations
```

---

## A) Manual Analysis

I read all three projects in full before writing the skill. The problems
below defined which detection signals it needed to know. Full reports live in
[`reports/`](reports/).

### code-smells-project (Flask, 780 lines)

| Sev. | Problem | Location | Why it matters |
|---|---|---|---|
| CRITICAL | Endpoint executes arbitrary client SQL | `app.py:59-78` | One request dumps the users table or drops the database |
| CRITICAL | SQL Injection via concatenation in every query | `models.py:110` (+18) | `' OR '1'='1' --` on login authenticates as admin |
| CRITICAL | Plaintext passwords, compared inside the `WHERE` | `models.py:105-111` | A `.db` leak hands over ready-to-use credentials |
| HIGH | Checkout without a transaction, with a stock race | `models.py:133-169` | Two requests for the last unit both succeed |
| MEDIUM | Duplicated validation that already diverged | `controllers.py:28-54` vs `72-90` | `PUT` accepts what `POST` rejects |
| MEDIUM | `str(e)` returned to the client in 17 handlers | `controllers.py:10-12` (+16) | Reveals table names — input for the injection above |
| LOW | Discount tiers as loose literals | `models.py:256-262` | Changing commercial policy means hunting the right `elif` |
| LOW | `cursor2`/`cursor3` and `print` as logging | `models.py:187` (+13) | A numbered name does not survive refactoring |

### ecommerce-api-legacy (Express, 180 lines)

| Sev. | Problem | Location | Why it matters |
|---|---|---|---|
| CRITICAL | Gateway `pk_live` key and database password versioned | `src/utils.js:2-6` | Allows operating the gateway on the company's behalf |
| CRITICAL | Hand-rolled, reversible password hashing | `src/utils.js:17-23` | Repeats the same Base64 pair 10,000 times, no salt |
| CRITICAL | Card number and API key written to logs | `src/AppManager.js:45` | Direct PCI DSS violation |
| HIGH | Delete leaves enrollments and payments orphaned | `src/AppManager.js:131-137` | Confirmed: report shows `"Unknown"` with 997.00 still counted |
| MEDIUM | Four-level N+1 in the report | `src/AppManager.js:83-106` | 50 courses × 30 enrollments → 3,000+ queries |
| MEDIUM | Callback errors ignored | `src/AppManager.js:104,106,133` | Delete responds 200 even when it fails |
| LOW | Variables `u`, `e`, `p`, `cid`, `cc` | `src/AppManager.js:29-33` | In JS, `e` conventionally means event or error — here it is email |
| LOW | Global cache nobody reads, which does not work | `src/utils.js:9-15` | `totalRevenue` is an exported primitive: always `0` for importers |

### task-manager-api (Flask + SQLAlchemy, 1,160 lines)

It already had `models/`, `routes/`, `services/` and `utils/`. A structure
existing does not mean responsibilities are in the right place.

| Sev. | Problem | Location | Why it matters |
|---|---|---|---|
| CRITICAL | Unsalted MD5 for passwords | `models/user.py:29,32` | The stored hash is `1234` in any rainbow table |
| CRITICAL | The hash ships in API responses | `models/user.py:21` | Leaks in 4 endpoints, including login |
| HIGH | No Controller layer exists | `routes/*.py` | `summary_report` runs 20+ queries inside the handler; `services/` holds one class nobody calls |
| HIGH | "Overdue task" rule rewritten 6 times | `models/task.py:50-59` + 5 handlers | The model exposes `is_overdue()` and no handler uses it |
| MEDIUM | 46 legacy Query API calls + 18 `utcnow()` | various | `LegacyAPIWarning` confirmed at runtime on SQLAlchemy 2.0.54 |
| MEDIUM | Nine bare `except:` blocks | `routes/task_routes.py:62` (+8) | They discard the exception with no log; production debugging is impossible |
| LOW | Constants defined and never imported | `utils/helpers.py:110-116` | The lists are retyped in five places |
| LOW | 52 lines of dead validation | `utils/helpers.py:57-108` | Whoever "fixes" it changes nothing in the API |

---

## B) Building the Skill

**SKILL.md is the prompt, references are the knowledge.** SKILL.md says what
to do and in what order; the references say what to know, loaded on demand —
the catalog only in Phase 2, the playbook only in Phase 3.

**Detection signals, not descriptions.** Each catalog entry answers "what do
I look for literally in the code". `"execute( receiving an expression with +,
%, .format() or an f-string"` is executable; `"unsafe queries"` depends on
the agent already knowing what to look for — and if it did, the skill would
be unnecessary.

**Catalog — 23 anti-patterns** (minimum required: 8), one for every problem
found in the manual analysis, otherwise the skill would not detect it:

| Severity | Anti-patterns |
|---|---|
| CRITICAL | hardcoded credentials · SQL injection · exposed arbitrary execution · God Class · sensitive data exposure · inadequate cryptography |
| HIGH | business logic in controller · coupling without DI · mutable global state · operation without transaction · delete without integrity · callback hell |
| MEDIUM | N+1 · duplication · missing or leaking error handling · missing validation · **deprecated APIs** · coupled configuration |
| LOW | magic numbers · dead code · naming · `print` as logging · redundant conditionals |

AP-17 (deprecated) carries 17 API/replacement pairs covering Python,
SQLAlchemy, Flask, Node and Express, and instructs checking the declared
version before classifying: `datetime.utcnow()` on Python 3.8 is merely
dated; on 3.12 it has an announced removal.

**Technology agnosticism**, through four decisions: manifest-based detection
(not extensions), covering six ecosystems; detection signals written in more
than one language; a playbook alternating Python and JavaScript on purpose;
and Phase 3 calibrated by architecture level — monolithic, partially
separated, or already layered.

### Challenges encountered

**Phase 3 had to diverge on project 3.** The first version described a fixed
sequence which, applied to `task-manager-api`, would have renamed `routes/`
to `views/` and recreated existing folders — a huge diff for no gain. Hence
the calibration by architecture level.

**Fixing a dangerous endpoint without breaking the contract.** `POST
/admin/query` accepted any SQL, with no authentication. Removing it would
break the contract; keeping it would be an audit failure. The way out was
separating the route from the capability: the endpoint responds, but only
with `DEBUG` enabled, requiring `X-Admin-Token`, accepting only `SELECT`, one
statement per request and a 100-row cap. The check runs after stripping SQL
comments, so `-- ; DROP TABLE` cannot be used as a disguise.

**Migrating `utcnow()` breaks date comparison.** Switching to
`now(timezone.utc)` made the overdue calculation compare a timezone-aware
datetime against the naive one SQLite returns — `TypeError`. The trap went
into the playbook (RP-14) along with the normalization helper.

---

## C) Results

| Project | Stack | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---:|---:|---:|---:|---:|
| code-smells-project | Flask | 6 | 4 | 4 | 4 | **18** |
| ecommerce-api-legacy | Express | 5 | 6 | 5 | 3 | **19** |
| task-manager-api | Flask+SQLAlchemy | 3 | 5 | 5 | 4 | **17** |

Project 3 has fewer CRITICAL findings despite being the largest: it already
uses an ORM and has partial separation. Its debt is leaked responsibility and
deprecated APIs, not raw structural failure.

### Structure before and after

| | Before | After |
|---|---|---|
| **P1** | 4 files at the root (`models.py` 314 lines, `controllers.py` 292) | 24 files: `config/`, `models/`, `services/`, `controllers/`, `routes/`, `middlewares/`, `validators/` |
| **P2** | 3 files (`AppManager.js`, 141 lines of database, routes and business) | 20 files: `config/`, `infra/`, `repositories/`, `services/`, `controllers/`, `routes/`, `middlewares/`, `validators/` |
| **P3** | `models/`, `routes/` (everything here), `services/` (1 dead class), `utils/` (60% dead) | same folders preserved + `controllers/`, `repositories/`, `config/`, `middlewares/`, `validators.py` |

### Gains measured at runtime

| Metric | Before | After |
|---|---:|---:|
| P1 · `GET /pedidos` (10 orders, 30 items) | 41 queries | **3** |
| P2 · financial report (50 courses × 30 enrollments) | ~3,051 queries | **1** |
| P3 · `GET /tasks` (11 tasks) | 23 queries | **1** |
| P3 · `GET /users` / `/categories` | 5 queries | **1** |
| P3 · `GET /reports/summary` | 20+ queries | **9** |

Security fixes, verified by real requests:

```
P1  login with ' OR '1'='1' --     before: 200 (entered as admin)     after: 401
P1  GET /health                    before: leaked secret_key/db_path  after: status and counts only
P1  GET /usuarios                  before: plaintext password column  after: field removed
P1  POST /admin/query "DROP ..."   before: 200, table dropped         after: 403
P1  order with insufficient stock  before: partial order written      after: 400 + rollback

P2  financial-report without token before: 200 with revenue and names after: 401
P2  checkout log                   before: card + pk_live key         after: cardLast4 only
P2  DELETE /api/users/1            before: report showed "Unknown"    after: history intact

P3  GET /users/1 and POST /login   before: MD5 hash in the body       after: field removed
P3  POST /tasks priority:"alta"    before: 500 swallowed by except:   after: 400 with a message
P3  DELETE /categories/1           before: tasks left with orphan FK  after: 0 orphans
```

### Validation checklist

| | P1 | P2 | P3 |
|---|:-:|:-:|:-:|
| **Phase 1** — language, framework, domain and file count correct | ok | ok | ok |
| **Phase 2** — report follows the template, findings cite file:line, ordered by severity | ok | ok | ok |
| **Phase 2** — minimum of 5 findings | 18 | 19 | 17 |
| **Phase 2** — deprecated APIs included | n/a¹ | ok | ok |
| **Phase 2** — pauses and asks for confirmation before Phase 3 | ok | ok | ok |
| **Phase 3** — MVC structure, configuration extracted, models/views/controllers separated | ok | ok | ok |
| **Phase 3** — centralized error handling and clear entry point | ok | ok | ok |
| **Phase 3** — application boots without errors | ok | ok | ok |
| **Phase 3** — original endpoints respond | 19/19² | 6/6 | 22/22 |

¹ P1 uses only current Flask 3.1.1 APIs — the absence is recorded in the
report, not omitted.
² Both `/admin/*` routes now require `X-Admin-Token` and development mode;
details in [`reports/audit-project-1.md`](reports/audit-project-1.md).

### Applications running after refactoring

Final validation: **44 requests, zero failures**, on a clean clone of the
repository. Structured log from P2 in operation — compare with the
`console.log` that printed the full card number and gateway key:

```json
{"level":"info","event":"server.started","port":3000,"env":"development"}
{"level":"info","event":"payment.charge","cardLast4":"4444","amount":997,"status":"PAID"}
{"level":"info","event":"checkout.concluido","enrollmentId":3,"userId":4,"courseId":1}
```

### Behavior across different stacks

Manifest-based detection was correct on all three stacks, and the
layer-boundary anti-patterns transported best, being syntax-independent. What
diverged was Phase 3 on P3: it introduced layers alongside what existed,
instead of creating the whole tree.

Some anti-patterns appeared in only one stack — callback hell only in Node,
and deprecated APIs yielded 64 occurrences in P3 against zero in P1. A
catalog built on a single stack would lack the asynchrony entry, and the
skill would have missed the double-response defect in the financial report.

**Observed limit:** the skill depends on the project fitting into Phase 1's
full read. The three total 2,100 lines; on a 100k-line system, Phase 1 would
need to sample per module and completeness would depend on that.

---

## D) How to Run

**Prerequisites:** [Claude Code](https://claude.com/claude-code), Python
3.10+ (P1 and P3), Node.js 18+ (P2).

### Running the skill

```bash
cd code-smells-project && claude "/refactor-arch"
cd ../ecommerce-api-legacy && claude "/refactor-arch"
cd ../task-manager-api && claude "/refactor-arch"
```

Phase 1 prints the detected stack. Phase 2 prints the report and **pauses**
at `Proceed with refactoring (Phase 3)? [y/n]`. With `y`, Phase 3 refactors
and validates; with `n`, it ends having delivered the report.

To use it on another project, copy the folder:

```bash
cp -R code-smells-project/.claude/skills/refactor-arch your-project/.claude/skills/
```

### Running the refactored projects

Each project ships an `.env.example`. Copy it to `.env` before booting.

```bash
# P1
cd code-smells-project
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && .venv/bin/python app.py

# P2
cd ecommerce-api-legacy
npm install && cp .env.example .env
PAYMENT_GATEWAY_KEY=pk_test_local ADMIN_TOKEN=tok npm start

# P3
cd task-manager-api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && .venv/bin/python seed.py && .venv/bin/python app.py
```

> **Port note on macOS:** the AirPlay Receiver holds port 5000. Since the port
> now comes from the environment, use `PORT=5001 .venv/bin/python app.py` —
> no need to edit code anymore. That was one of the coupled-configuration
> findings.

### Validating

```bash
for r in / /health /produtos /usuarios /pedidos /relatorios/vendas; do
  printf "%-22s -> %s\n" "$r" \
    "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5001$r)"
done

# security fixes
curl http://localhost:5001/health                    # no secret_key
curl http://localhost:5002/users/1                   # no password hash
curl -H 'X-Admin-Token: tok' http://localhost:3000/api/admin/financial-report
```

P1's `/admin/*` routes require `DEBUG=true`, `ADMIN_TOKEN` and the
`X-Admin-Token` header. `/admin/query` accepts only `SELECT`, one statement
per request, 100 rows maximum — writes return 403.

---

## Repository structure

```
mba-ia-refactor-projects-skill/
├── README.md
├── reports/audit-project-{1,2,3}.md     # 18, 19 and 17 findings
├── code-smells-project/                 # Flask — refactored
├── ecommerce-api-legacy/                # Express — refactored
└── task-manager-api/                    # Flask+SQLAlchemy — refactored
      └── .claude/skills/refactor-arch/  # the skill, identical in all 3
```

> **A note on identifiers:** code comments and documentation are in English;
> identifiers, database columns and JSON response keys remain in Portuguese
> because they are the original projects' public API contract — renaming them
> would break the endpoints the refactoring was meant to preserve.
