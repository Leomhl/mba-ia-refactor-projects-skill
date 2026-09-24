```
==================================
ARCHITECTURE AUDIT REPORT
==================================
Project: code-smells-project
Stack:   Python 3.12 + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-09-21
```

## Summary

CRITICAL: 6 | HIGH: 4 | MEDIUM: 4 | LOW: 4

## Deprecated APIs

No deprecated APIs found. The project declares Flask 3.1.1 and uses only
current APIs for that version. The cryptographic security problem does exist
(unhashed passwords), but it is recorded as AP-06, not AP-17.

## Findings

### [CRITICAL] Arbitrary SQL execution over HTTP (AP-03)

**File:** `app.py:59-78`

**Description:** The `POST /admin/query` route reads the `sql` field from the
request body and hands it straight to `cursor.execute()`, with no
authentication, no allowlist of statements and no origin restriction —
`CORS(app)` on `app.py:9` opens it to any domain. The `else` branch on line
74 also calls `db.commit()`, so write statements are persisted.

**Impact:** A single request dumps the entire `usuarios` table with its
plaintext passwords, or executes `DROP TABLE pedidos`. No exploit is needed:
the endpoint does the work.

**Recommendation:** Reduce the endpoint to a read-only inspection query
behind authentication: require an administrative token, restrict it to
`SELECT`, reject more than one statement per request and cap the number of
rows returned. What cannot remain is the write capability and the absence of
authentication (playbook RP-06).

### [CRITICAL] Destructive endpoint without authentication (AP-03)

**File:** `app.py:47-57`

**Description:** `POST /admin/reset-db` deletes all four database tables in
sequence and commits. The route checks no identity, role, token or origin.
The `/admin` prefix is merely a naming convention — no middleware is bound to
it.

**Impact:** Anyone who discovers the URL wipes the production database with a
`curl`. Combined with the unrestricted `CORS(app)`, a malicious page triggers
the call from a logged-in user's browser.

**Recommendation:** Require an administrative token from the environment and
block the route when the application is not in development mode (playbook
RP-01 for the token, RP-06 for the route layer).

### [CRITICAL] SQL Injection via string concatenation (AP-02)

**File:** `models.py:28`, `models.py:47-50`, `models.py:57-61`, `models.py:68`,
`models.py:92`, `models.py:109-111`, `models.py:126-129`, `models.py:140`,
`models.py:148-151`, `models.py:155`, `models.py:157-161`, `models.py:163-166`,
`models.py:174`, `models.py:188`, `models.py:192`, `models.py:220`,
`models.py:224`, `models.py:279-281`, `models.py:289-297`

**Description:** Not a single query in the project is parameterized. All are
built with string concatenation. The most exposed cases take raw client
input: `login_usuario` (lines 109-111) interpolates `email` and `senha` from
the `POST /login` body; `buscar_produtos` (lines 289-297) accumulates the
`WHERE` clause by concatenating the search term from the query string,
including inside the `LIKE '%...%'`; `criar_produto` (47-50) and
`criar_usuario` (126-129) interpolate the `INSERT` fields.

**Impact:** `POST /login` with `{"email": "' OR '1'='1' --", "senha": "x"}`
authenticates as the first user in the table — which, per the seed at
`database.py:76`, is the administrator. The same vector on
`GET /produtos/busca?q=` allows a `UNION SELECT` to extract any table.

**Recommendation:** Convert every query to `?` placeholders with a separate
parameter tuple, including the dynamic ones, accumulating values in a list
parallel to the clause (playbook RP-02).

### [CRITICAL] Passwords stored and compared in plaintext (AP-06)

**File:** `database.py:76-79`, `models.py:105-111`, `models.py:122-131`,
`models.py:84`, `models.py:100`

**Description:** The seed writes the literal passwords `admin123`, `123456`
and `senha123` into the `usuarios.senha` column (`database.py:76-79`).
`criar_usuario` (122-131) inserts whatever the client sent, untransformed.
`login_usuario` (105-111) authenticates by comparing the password inside the
query's `WHERE` clause — meaning the plaintext travels to the database as a
search criterion. The serializers on lines 84 and 100 still return the
field.

**Impact:** A leak of the `loja.db` file — or any of the injection vectors
above — hands over ready-to-use credentials, with no cracking effort. Since
users reuse passwords, the damage extends beyond this application.

**Recommendation:** Hash with a KDF (Werkzeug's `generate_password_hash`,
already available as a Flask transitive dependency) and verify with
`check_password_hash`. For the existing database, re-hash transparently on
the first successful login (playbook RP-12).

### [CRITICAL] Sensitive data exposed in responses (AP-05)

**File:** `controllers.py:285-289`, `models.py:84`, `models.py:100`

**Description:** `GET /health` returns, in a public body, the `secret_key`
(`"minha-chave-super-secreta-123"`), the `debug` flag, the database file path
(`db_path`) and the environment label. In parallel, `get_todos_usuarios` and
`get_usuario_por_id` include the `senha` column in the serialized dictionary,
which goes untouched into `GET /usuarios` and `GET /usuarios/<id>`.

**Impact:** `GET /health` is typically the route left open at the load
balancer and monitoring layer. It hands out the session signing key. And
`GET /usuarios` is, in practice, a credential dump reachable without
authentication.

**Recommendation:** Reduce `/health` to status and database availability, and
remove the password field from the user serializer (playbook RP-12).

### [CRITICAL] God Module spanning four domains (AP-04)

**File:** `models.py:1-314`, `controllers.py:1-292`

**Description:** `models.py` combines data access, serialization, checkout
business rules (`criar_pedido`, 133-169) and financial calculation
(`relatorio_vendas`, 235-273) for the product, user, order and report
domains. `controllers.py` concentrates the 17 handlers for those same four
domains. There is no layer directory in the project — the 4 files sit at the
root.

**Impact:** Any change, in any domain, touches the same two files:
guaranteed merge conflicts on a team with more than one person. Testing the
discount rule requires importing the whole module, which in turn opens a
database connection on importing `database`.

**Recommendation:** Split by domain first and by layer second, producing
`models/`, `controllers/`, `services/` and `routes/` with one module per
entity; move checkout and reporting into Services, since they span more than
one entity (playbook RP-03).

### [HIGH] Business rules and side effects inside the Controller (AP-07)

**File:** `controllers.py:208-210`, `controllers.py:247-250`,
`controllers.py:266-274`, `controllers.py:43-54`

**Description:** `criar_pedido` fires three notifications (email, SMS and
push, lines 208-210) inline in the handler. `atualizar_status_pedido` decides
notifications via an `if` over domain state (247-250), including the
"cancelled returns stock" rule — which is written as a `print` message but
never implemented. `health_check` opens a cursor and runs four queries
directly in the handler (266-274). Price-range and valid-category rules sit
in sequential `if`s in the middle of validation (43-54).

**Impact:** The notification rule is neither reusable nor testable without
booting an HTTP server. Worse: the comment on line 250 documents a business
rule (stock return on cancellation) that the system does not execute — stock
decremented on a cancelled order never comes back.

**Recommendation:** Extract a `NotificacaoService` and a `PedidoService` that
own the flow; the Controller returns to receiving, delegating and responding
(playbook RP-04).

### [HIGH] Mutable global connection shared across threads (AP-08, AP-09)

**File:** `database.py:4-11`

**Description:** The connection is a module singleton (`db_connection = None`
on line 4) initialized via `global` inside `get_db()`, with
`check_same_thread=False` on line 10 — which disables precisely SQLite's
protection against concurrent use of the same connection. Every module
imports `get_db` directly, so there is no injection point.

**Impact:** With the server handling parallel requests, two cursors share the
same connection and the same implicit transaction: one request's `commit`
persists another's partial work. Testing any function requires a real
database file — there is no way to inject a substitute.

**Recommendation:** Turn connection creation into a factory that receives the
configuration, and inject the dependency into the data modules from the
composition root (playbook RP-05).

### [HIGH] Checkout without a transaction and with a stock race (AP-10)

**File:** `models.py:133-169`

**Description:** `criar_pedido` performs the stock-check `SELECT` in the loop
on lines 139-146, inserts the order on line 148, and only then, in the second
loop (154-166), writes the items and decrements stock. The only `commit` is
on line 168, with no explicit `BEGIN` and no `rollback` on error. The stock
check and the decrement happen in separate statements.

**Impact:** Two concurrent requests for the last item in stock both pass the
check on line 144 and both execute the `UPDATE` on line 163 — stock goes
negative. An exception in the middle of the second loop leaves an order
created with half its items and stock partially decremented.

**Recommendation:** Wrap the operation in an explicit transaction with
rollback, and move the stock condition into the `UPDATE` itself
(`WHERE id = ? AND estoque >= ?`), using `rowcount == 0` as the failure
signal (playbook RP-08).

### [HIGH] N+1 query in order listings (AP-13)

**File:** `models.py:187-199`, `models.py:219-231`

**Description:** `get_pedidos_usuario` and `get_todos_pedidos` are duplicates
of one another and both query in cascade: one query for the orders, one for
each order's items (lines 188 and 220), and one more for each item's product
name (192 and 224). The auxiliary cursors are created inside the loops and
named `cursor2` and `cursor3`.

**Impact:** `GET /pedidos` with 100 orders of 3 items each fires 401 queries.
The cost grows with the product of orders by items, not with the number of
records returned.

**Recommendation:** Replace with two queries using a `JOIN` between
`itens_pedido` and `produtos`, filtering by `pedido_id IN (...)` and grouping
the items in memory (playbook RP-07).

### [MEDIUM] Validation block duplicated between create and update (AP-14)

**File:** `controllers.py:28-54`, `controllers.py:72-90`

**Description:** Product validations appear twice, with the same messages and
the same literal limits. The copies have already diverged: `criar_produto`
validates name length (lines 47-50) and the category list (52-54);
`atualizar_produto` validates neither.

**Impact:** `PUT /produtos/<id>` accepts a one-character name and a
nonexistent category that `POST /produtos` rejects. The same entity ends up
with two sets of invariants depending on the entry point.

**Recommendation:** Extract a single validator with a partial mode for `PUT`,
reused by both handlers (playbook RP-13).

### [MEDIUM] Repeated error handling that leaks internal detail (AP-15)

**File:** `controllers.py:10-12`, `controllers.py:21-22`, `controllers.py:60-62`,
`controllers.py:95-96`, `controllers.py:108-109`, `controllers.py:125-126`,
`controllers.py:133-134`, `controllers.py:143-144` (+ 9 more occurrences in
the same file)

**Description:** All 17 handlers repeat the same `try/except Exception`,
returning `str(e)` in the response body with status 500. No error handler is
registered on the application.

**Impact:** The SQLite exception message reaches the client and reveals table
and column names — direct input for building the AP-02 injection. And since
every error becomes a 500, validation failures and infrastructure failures
are indistinguishable to API consumers.

**Recommendation:** Register global handlers with an application exception
hierarchy, sending technical detail to the log and returning a generic
message to the client (playbook RP-11).

### [MEDIUM] Missing input validation and type checking (AP-16)

**File:** `controllers.py:43-46`, `controllers.py:87-90`, `controllers.py:7`,
`controllers.py:130`, `controllers.py:232`

**Description:** The `preco < 0` and `estoque < 0` comparisons (43-46 and
87-90) happen without checking the received value's type. None of the list
endpoints has pagination: `/produtos` (line 7), `/usuarios` (130) and
`/pedidos` (232) return the entire table.

**Impact:** `POST /produtos` with `{"preco": "abc"}` raises `TypeError` and
results in a 500, when a 400 with a validation message would be correct.
Unbounded listings degrade proportionally as the database grows, and
`/pedidos` compounds this with the N+1 above.

**Recommendation:** Validate types before comparing and introduce
`limit`/`offset` pagination with a maximum cap (playbook RP-13).

### [MEDIUM] Configuration and secrets coupled to the code (AP-18)

**File:** `app.py:7-9`, `app.py:88`, `database.py:5`

**Description:** `SECRET_KEY` (line 7) and `DEBUG = True` (line 8) are
literals. `CORS(app)` (line 9) opens any origin, with no domain list.
`app.run` pins `host="0.0.0.0"`, `port=5000` and `debug=True` (line 88). The
database path is a literal on `database.py:5`. There is no `.env.example` in
the project.

**Impact:** `debug=True` exposes the Werkzeug interactive console, which
executes arbitrary Python on the server. Promoting to another environment
requires editing source. The fixed port also prevents booting on machines
where 5000 is taken — on macOS, the AirPlay Receiver holds that port by
default.

**Recommendation:** Extract a configuration module reading environment
variables, with `DEBUG` defaulting to `false` when absent, and publish
`.env.example` (playbook RP-01).

### [LOW] Magic numbers and literal value lists (AP-19)

**File:** `controllers.py:52`, `controllers.py:242`, `models.py:256-262`,
`controllers.py:47-50`

**Description:** The valid-category list is written inline in the handler
(line 52), as is the order status list (242). The revenue discount tiers
(`models.py:256-262`) use literal thresholds and percentages, with no name
identifying the commercial policy. Name length limits (2 and 200) appear
loose on lines 47-50.

**Impact:** Changing the discount policy requires finding the right `elif`
inside a reporting function. Since the same values appear in different
places, the chance of updating one and forgetting the other is high.

**Recommendation:** Promote them to named constants and turn the discount
tiers into an iterable data structure (playbook RP-15).

### [LOW] Poor naming and builtin shadowing (AP-21)

**File:** `models.py:187`, `models.py:191`, `models.py:219`, `models.py:223`,
`controllers.py:14`, `controllers.py:64`, `controllers.py:98`,
`controllers.py:136`

**Description:** Auxiliary cursors are numbered `cursor2` and `cursor3`, with
no indication of what they query. Eight functions take a parameter named
`id`, shadowing the Python builtin of the same name. The project mixes
languages within the same layer: `criar_produto` sits beside
`get_todos_produtos`.

**Impact:** A numbered name does not survive refactoring — whoever removes
`cursor2` leaves `cursor3` with orphaned numbering. Shadowing `id` is
harmless in these functions, but breaks silently if someone needs the builtin
in the same scope.

**Recommendation:** Name by content (`cursor_itens`, `cursor_produto`),
replace `id` with `produto_id`/`usuario_id` and standardize identifier
language (playbook RP-03 during the domain split).

### [LOW] `print` as a logging strategy (AP-22)

**File:** `controllers.py:8`, `controllers.py:11`, `controllers.py:57`,
`controllers.py:61`, `controllers.py:106`, `controllers.py:161`,
`controllers.py:179`, `controllers.py:182`, `controllers.py:208-210`,
`controllers.py:219`, `controllers.py:248`, `controllers.py:250`,
`app.py:56`, `app.py:83-86`

**Description:** There is no logging library in the project. The 14
occurrences use `print` with string concatenation, without severity levels
and without structure. Line 179 logs the email address on successful login;
lines 208-210 simulate notification delivery via `print`.

**Impact:** Without levels, errors cannot be filtered from noise in
production. Without structure, nothing can be indexed. And the login log
(line 179) writes a user identifier to stdout with no retention control.

**Recommendation:** Use Flask's `app.logger` with appropriate levels and
structured fields, excluding personal data (playbook RP-16).

### [LOW] Unused imports (AP-20)

**File:** `models.py:2`, `database.py:2`

**Description:** `models.py` imports `sqlite3` on line 2 without using any
symbol from the module — all database access is mediated by `get_db()`.
`database.py` imports `os` on line 2 and never uses it.

**Impact:** It suggests a direct driver dependency that does not exist, and
it hinders the refactoring itself: whoever sets out to swap the database
searches for `sqlite3` usages and finds a dead import.

**Recommendation:** Remove both imports.

```
==================================
Total: 18 findings
==================================
```

## Out of scope

Two items identified during the audit are not resolved by Phase 3 because
they require a product decision:

1. **Complete absence of authentication on business endpoints.** The system
   has `POST /login`, but it issues no credential — it returns the user's
   data and ends. No route verifies identity. Introducing sessions or JWT
   changes the contract for every existing client and must be decided by the
   team, not by the refactoring.

2. **Stock return rule on order cancellation.** The code documents the intent
   at `controllers.py:250` but never implemented it. Implementing it now is a
   business behavior change, not refactoring — and it needs a decision about
   orders already cancelled in the database.

## Note on the endpoint contract

Phase 3 preserves all 19 original endpoints. The two administrative routes
keep responding, but with behavior restricted per the CRITICAL AP-03
findings:

**`POST /admin/reset-db`** now requires the `X-Admin-Token` header matching
`ADMIN_TOKEN`, and is refused when the application is not in development
mode.

**`POST /admin/query`** stops being arbitrary execution and becomes an
inspection query, under four cumulative restrictions:

| Restriction | Effect |
|---|---|
| Only responds with `DEBUG` enabled | Unavailable in the production profile |
| Requires `X-Admin-Token` | Without a valid token, 403 |
| Accepts only `SELECT`/`WITH` | `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA` and `VACUUM` are refused |
| One statement per request | Stacking via `;` is refused; `cursor.execute()` in sqlite3 also rejects multiple statements |

The response is capped at 100 rows, and no write path is committed. The
forbidden-keyword check runs after stripping comments (`--` and `/* */`), so
they cannot be used as a disguise.

The criterion applied: preserving the route is legitimate, preserving the
ability to execute arbitrary SQL without authentication is not. The endpoint
responds; what it accepts is what changed.
