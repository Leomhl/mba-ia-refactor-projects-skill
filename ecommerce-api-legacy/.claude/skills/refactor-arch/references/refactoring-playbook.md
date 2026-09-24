# Refactoring playbook

Phase 3 transformations. Each pattern resolves one or more catalog
anti-patterns and carries before/after code.

The examples alternate between Python and JavaScript on purpose: what matters
is the structural move, not the syntax. Translate to the project's language.

---

## RP-01 — Extract configuration to the environment

Resolves AP-01, AP-18.

Do this first. The transformations that follow depend on there being a place
for environment values to go.

**Before**

```python
app.config["SECRET_KEY"] = "my-super-secret-key-123"
app.config["DEBUG"] = True
app.run(host="0.0.0.0", port=5000, debug=True)
```

**After**

```python
# config/settings.py
import os

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DB_PATH = os.getenv("DB_PATH", "store.db")

settings = Settings()
```

```bash
# .env.example
SECRET_KEY=replace-with-a-random-value
DEBUG=false
HOST=127.0.0.1
PORT=5000
DB_PATH=store.db
```

Points to watch:

- The `DEBUG` default is `false`. A missing variable must never enable debug
  mode.
- The `HOST` default is `127.0.0.1`, not `0.0.0.0` — exposing on all
  interfaces is a deployment decision, not a development default.
- A configurable `PORT` resolves local port conflicts without editing code.
- The secret that was in the code has already leaked: besides removing it,
  the value must be rotated. Record that in the report.

---

## RP-02 — Parameterize queries

Resolves AP-02.

**Before**

```python
cursor.execute("SELECT * FROM users WHERE email = '" + email + "' AND password = '" + password + "'")
```

**After**

```python
cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
```

A dynamic query without concatenating values — build the clause, accumulate
the parameters:

```python
def search(term=None, category=None, max_price=None):
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if term:
        sql += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{term}%", f"%{term}%"])
    if category:
        sql += " AND category = ?"
        params.append(category)
    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)
    cursor.execute(sql, params)
```

The `LIKE` wildcard goes into the **parameter**, not into the SQL string.
Column and table names cannot be parameterized — if they must be dynamic,
validate them against a closed allowlist of names.

---

## RP-03 — Split the God Module by domain

Resolves AP-04.

Cut by domain first, by layer second. Cutting by layer alone produces a
`models.py` with 300 lines spanning four domains — the same problem with a
new name.

**Before**

```
models.py        # products + users + orders + reports, 314 lines
controllers.py   # every handler, 292 lines
```

**After**

```
models/
├── product_model.py
├── user_model.py
└── order_model.py
controllers/
├── product_controller.py
├── user_controller.py
└── order_controller.py
services/
├── order_service.py       # checkout: transaction across order, item and stock
└── report_service.py      # aggregations and discount tiers
```

A safe routine:

1. List the functions and group them by the entity each one touches.
2. Move one domain at a time, keeping the code running between steps.
3. Fix the imports.
4. Run the validation.
5. Only then delete the original file.

A function that touches several entities (checkout, report) goes to a
Service, not to one entity's Model.

---

## RP-04 — Move business rules from Controller to Service

Resolves AP-07.

**Before** (JavaScript, rule inside the route)

```javascript
app.post('/api/checkout', (req, res) => {
    let status = req.body.card.startsWith("4") ? "PAID" : "DENIED";
    if (status === "DENIED") return res.status(400).send("Payment declined");
    db.run("INSERT INTO enrollments ...", [userId, cid], function(err) {
        db.run("INSERT INTO payments ...", [this.lastID, course.price, status]);
    });
});
```

**After**

```javascript
// services/CheckoutService.js
class CheckoutService {
    constructor(userRepo, courseRepo, enrollmentRepo, paymentGateway) {
        this.userRepo = userRepo;
        this.courseRepo = courseRepo;
        this.enrollmentRepo = enrollmentRepo;
        this.paymentGateway = paymentGateway;
    }

    async execute({ name, email, password, courseId, card }) {
        const course = await this.courseRepo.findActiveById(courseId);
        if (!course) throw new NotFoundError('Course not found');

        const user = await this.userRepo.findOrCreate({ name, email, password });
        const payment = await this.paymentGateway.charge(card, course.price);
        if (payment.status !== 'PAID') throw new PaymentDeclinedError();

        return this.enrollmentRepo.enroll(user.id, course.id, payment);
    }
}

// controllers/CheckoutController.js
async function checkout(req, res, next) {
    try {
        const result = await checkoutService.execute(req.body);
        res.status(201).json(result);
    } catch (err) {
        next(err);
    }
}
```

The Controller became protocol translation. The rule ("a declined card
cancels the enrollment") is now testable without booting an HTTP server.

---

## RP-05 — Inject dependencies instead of instantiating

Resolves AP-08, AP-09.

**Before**

```javascript
class AppManager {
    constructor() {
        this.db = new sqlite3.Database(':memory:');   // coupled to the driver
    }
}
```

**After**

```javascript
class UserRepository {
    constructor(db) {          // receives, does not create
        this.db = db;
    }
    findByEmail(email) {
        return this.db.get("SELECT * FROM users WHERE email = ?", [email]);
    }
}

// app.js — composition root: the only place that knows the implementations
const db = createConnection(config.dbPath);
const userRepo = new UserRepository(db);
const checkoutService = new CheckoutService(userRepo, courseRepo, ...);
```

In Python, the equivalent is receiving the connection as a parameter or using
the application context, instead of `global db_connection`.

Concrete gain: tests inject a fake repository and the suite runs with no
database.

---

## RP-06 — Turn routes into pure declaration

Resolves AP-04, AP-07.

**Before** (Python — route with logic embedded in the entry point)

```python
@app.route("/admin/query", methods=["POST"])
def run_query():
    data = request.get_json()
    cursor.execute(data.get("sql", ""))     # RCE
    ...
```

**After**

```python
# routes/product_routes.py
from flask import Blueprint
from controllers import product_controller

product_bp = Blueprint("products", __name__, url_prefix="/products")

product_bp.add_url_rule("", "list", product_controller.list, methods=["GET"])
product_bp.add_url_rule("/search", "search", product_controller.search, methods=["GET"])
product_bp.add_url_rule("/<int:id>", "get", product_controller.get, methods=["GET"])
```

The static route (`/search`) comes before the parameterized one
(`/<int:id>`) — with `<int:...>` Flask disambiguates by type, but explicit
ordering avoids surprises when the converter changes.

### Arbitrary execution endpoints

A route that executes SQL or commands coming from the client (AP-03) cannot
stay as it is. There are two legitimate ways out, and the choice depends on
who consumes the API:

**Remove it**, when nothing depends on the route. This is the safest option
and requires no maintenance.

**Restrict it**, when the contract must be preserved. The route keeps
responding but loses the dangerous capability. Cumulative restrictions — none
of them is sufficient alone:

1. Available outside production only (`DEBUG` enabled).
2. Requires an administrative credential from the environment.
3. Read-only: accept `SELECT`/`WITH`, reject `INSERT`, `UPDATE`, `DELETE`,
   `DROP`, `ALTER`, `CREATE`, `ATTACH` and `PRAGMA`.
4. One statement per request, to block stacking via `;`.
5. A row cap on the response.

```python
def _require_read_only(query):
    # Comments are stripped before the check: "-- ; DROP TABLE x" would
    # sail through a naive check against the raw text.
    clean = re.sub(r"--[^\n]*|/\*.*?\*/", " ", query, flags=re.S).strip()

    if not clean.lower().startswith(("select", "with")):
        raise ForbiddenError("Only SELECT queries are allowed")

    body = clean.rstrip().rstrip(";")
    if ";" in body:
        raise ForbiddenError("Only one statement per request")

    forbidden = {"attach", "detach", "pragma", "insert", "update", "delete",
                 "drop", "alter", "create", "replace", "vacuum"}
    found = set(re.findall(r"[a-z_]+", body.lower())) & forbidden
    if found:
        raise ForbiddenError("Statement not allowed: " + ", ".join(sorted(found)))
```

The driver helps: `cursor.execute()` in `sqlite3` rejects multiple statements
by nature — the check in item 4 is defense in depth, not the only barrier.

The criterion: preserving the **route** is legitimate; preserving the
**ability to execute arbitrary commands without authentication** is not. If
the operation is needed for routine maintenance, its best home is still a CLI
command, not an HTTP route.

---

## RP-07 — Eliminate N+1 with JOIN or eager loading

Resolves AP-13.

**Before** — 1 + N × 2 queries

```python
for row in orders:
    items = cursor.execute("SELECT * FROM order_items WHERE order_id = " + str(row["id"]))
    for item in items:
        product = cursor.execute("SELECT name FROM products WHERE id = " + str(item["product_id"]))
```

**After** — 2 queries, regardless of N

```python
cursor.execute("SELECT * FROM orders")
orders = cursor.fetchall()
if not orders:
    return []

ids = [o["id"] for o in orders]
placeholders = ",".join("?" * len(ids))
cursor.execute(f"""
    SELECT i.order_id, i.product_id, i.quantity, i.unit_price, p.name AS product_name
    FROM order_items i
    JOIN products p ON p.id = i.product_id
    WHERE i.order_id IN ({placeholders})
""", ids)

items_by_order = defaultdict(list)
for item in cursor.fetchall():
    items_by_order[item["order_id"]].append(dict(item))
```

The f-string here interpolates only the `?` placeholders generated from the
count — never values. The values still travel in the parameter list.

With an ORM, the equivalent is declaring eager loading:

```python
tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
```

---

## RP-08 — Wrap related writes in a transaction

Resolves AP-10.

**Before**

```python
cursor.execute("INSERT INTO orders ...")
for item in items:
    cursor.execute("INSERT INTO order_items ...")
    cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", ...)
db.commit()
```

A failure on the third item leaves the order created, two items written and
stock partially decremented.

**After**

```python
try:
    db.execute("BEGIN")
    cursor.execute("INSERT INTO orders (user_id, status, total) VALUES (?, ?, ?)", ...)
    order_id = cursor.lastrowid
    for item in items:
        cursor.execute("""
            UPDATE products SET stock = stock - ?
            WHERE id = ? AND stock >= ?
        """, (item["quantity"], item["product_id"], item["quantity"]))
        if cursor.rowcount == 0:
            raise InsufficientStockError(item["product_id"])
        cursor.execute("INSERT INTO order_items (...) VALUES (?, ?, ?, ?)", ...)
    db.commit()
except Exception:
    db.rollback()
    raise
```

The detail that closes the race: the `stock >= ?` condition goes **inside**
the `UPDATE`, and `rowcount == 0` signals the failure. Checking stock
beforehand with a separate `SELECT` lets two concurrent requests both pass
the check and drive stock negative.

---

## RP-09 — Fix referential integrity on delete

Resolves AP-11.

**Before**

```javascript
app.delete('/api/users/:id', (req, res) => {
    db.run("DELETE FROM users WHERE id = ?", [req.params.id], () => {
        res.send("User deleted, but enrollments were left dirty in the database.");
    });
});
```

**After** — declare the constraint in the schema:

```sql
CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT
);
```

In SQLite, FK checking is off by default and must be enabled per connection:

```javascript
db.run("PRAGMA foreign_keys = ON");
```

Choose per relationship: `CASCADE` when the child cannot exist without the
parent; `RESTRICT` when deleting the parent should be blocked; soft delete
(`active = false`) when history must survive — the payment case, which cannot
vanish because a user was removed.

---

## RP-10 — Replace callback hell with async/await

Resolves AP-12.

**Before** — manual counters, four levels, possible double response

```javascript
this.db.all("SELECT * FROM courses", [], (err, courses) => {
    let coursesPending = courses.length;
    courses.forEach(c => {
        this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
            let enrPending = enrollments.length;
            enrollments.forEach(enr => {
                this.db.get("SELECT name FROM users WHERE id = ?", [enr.user_id], (err, user) => {
                    enrPending--;
                    if (enrPending === 0) { coursesPending--; if (coursesPending === 0) res.json(report); }
                });
            });
        });
    });
});
```

**After**

```javascript
// infra/db.js — promisify the driver once
const { promisify } = require('util');

function createDb(path) {
    const db = new sqlite3.Database(path);
    return {
        all: promisify(db.all.bind(db)),
        get: promisify(db.get.bind(db)),
        run: promisify(db.run.bind(db)),
    };
}

// services/ReportService.js
async function financialReport() {
    const rows = await db.all(`
        SELECT c.title AS course, u.name AS student, p.amount, p.status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u       ON u.id = e.user_id
        LEFT JOIN payments p    ON p.enrollment_id = e.id
    `);
    return groupByCourse(rows);
}
```

The rewrite resolved two anti-patterns at once: the nesting (AP-12) and the
N+1 (AP-13), because the JOIN removed the per-item queries.

A note on `sqlite3` and `lastID`: `promisify` over `db.run` loses the `this`
that carries `lastID`. When you need the inserted id, wrap it manually:

```javascript
function run(sql, params) {
    return new Promise((resolve, reject) => {
        db.run(sql, params, function (err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
}
```

---

## RP-11 — Centralize error handling

Resolves AP-15.

**Before** — the same block in 18 handlers

```python
def list_products():
    try:
        return jsonify({"data": models.get_all_products()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500     # leaks internals
```

**After**

```python
# middlewares/error_handler.py
class AppError(Exception):
    status_code = 500
    message = "Internal error"

class NotFoundError(AppError):
    status_code = 404
    message = "Resource not found"

class ValidationError(AppError):
    status_code = 400

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": err.message, "success": False}), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Unhandled error")      # detail goes to the log
        return jsonify({"error": "Internal error", "success": False}), 500
```

```python
# controllers/product_controller.py
def list():
    return jsonify({"data": product_model.list(), "success": True}), 200
```

The technical message goes to the log; the client gets a generic one. The
Controller shrank because the error path left it.

In Express, the equivalent is the four-argument middleware
`(err, req, res, next)` registered **after** the routes, with handlers
calling `next(err)`.

---

## RP-12 — Replace weak hashing with a KDF

Resolves AP-06.

**Before**

```python
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()
```

**After**

```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password = generate_password_hash(pwd)      # pbkdf2-sha256 with salt

def check_password(self, pwd):
    return check_password_hash(self.password, pwd)
```

In Node, `bcrypt.hash(pwd, 12)` / `bcrypt.compare(pwd, hash)`.

Migrating existing hashes: you cannot convert MD5 to bcrypt without the
original password. The standard approach is to re-hash on the next successful
login — verify against the old format, and if it passes, write the new one.
Meanwhile the MD5 hashes remain in the database; record in the report that
full migration depends on the users' login cycle.

Mandatory companion change: remove `password` from the serializer (AP-05). A
strong hash that ships in an HTTP response protects nothing.

---

## RP-13 — Extract duplicated validation

Resolves AP-14, AP-16.

**Before** — the same 12 lines in `create` and `update`

```python
if "name" not in data: return jsonify({"error": "Name is required"}), 400
if data["price"] < 0:  return jsonify({"error": "Price cannot be negative"}), 400
if len(data["name"]) < 2: return jsonify({"error": "Name too short"}), 400
```

**After**

```python
# validators/product_validator.py
NAME_MIN, NAME_MAX = 2, 200
VALID_CATEGORIES = ("electronics", "furniture", "apparel", "general", "books")

def validate_product(data, partial=False):
    if not data:
        raise ValidationError("Empty request body")

    required = () if partial else ("name", "price", "stock")
    for field in required:
        if field not in data:
            raise ValidationError(f"{field} is required")

    if "name" in data and not NAME_MIN <= len(data["name"].strip()) <= NAME_MAX:
        raise ValidationError(f"name must be between {NAME_MIN} and {NAME_MAX} characters")

    if "price" in data:
        if not isinstance(data["price"], (int, float)):
            raise ValidationError("price must be numeric")
        if data["price"] < 0:
            raise ValidationError("price cannot be negative")

    if "category" in data and data["category"] not in VALID_CATEGORIES:
        raise ValidationError(f"invalid category; use one of {VALID_CATEGORIES}")

    return data
```

The type check before the comparison is not a detail: `data["price"] < 0`
with `price` arriving as a string raises `TypeError` and returns 500 where it
should be 400.

The `partial` parameter lets the same function serve `PUT`, where fields are
optional.

---

## RP-14 — Replace deprecated APIs

Resolves AP-17.

A mechanical swap, but check the semantics — not every replacement is an
exact equivalent.

```python
# Python / SQLAlchemy
datetime.utcnow()               → datetime.now(timezone.utc)
Model.query.get(id)             → db.session.get(Model, id)
Model.query.filter_by(x=1).all()→ db.session.scalars(select(Model).filter_by(x=1)).all()
hashlib.md5(pwd)                → generate_password_hash(pwd)
```

```javascript
// Node / Express
new Buffer(str)                 → Buffer.from(str)
res.send(404, body)             → res.status(404).send(body)
str.substr(0, 2)                → str.slice(0, 2)
util.isArray(x)                 → Array.isArray(x)
crypto.createCipher(...)        → crypto.createCipheriv(...)
```

Careful with `datetime.utcnow()` → `datetime.now(timezone.utc)`: the first
returns a naive datetime, the second a timezone-aware one. Comparing one to
the other raises `TypeError`. When migrating, replace **all** occurrences at
once, including columns with `default=datetime.utcnow`, and check the
comparisons (`due_date < now`) that would now mix the two types.

---

## RP-15 — Name constants and extract tiered rules

Resolves AP-19.

**Before**

```python
if revenue > 10000:  discount = revenue * 0.1
elif revenue > 5000: discount = revenue * 0.05
elif revenue > 1000: discount = revenue * 0.02
```

**After**

```python
# services/discount.py
DISCOUNT_TIERS = (
    (10_000, 0.10),
    ( 5_000, 0.05),
    ( 1_000, 0.02),
)

def calculate_discount(revenue):
    for minimum, rate in DISCOUNT_TIERS:
        if revenue > minimum:
            return round(revenue * rate, 2)
    return 0.0
```

Changing the commercial policy became editing a tuple, and the rule is now
testable in isolation. The tiers must stay in descending order — worth a
comment or an `assert` if the list grows.

---

## RP-16 — Replace print with structured logging

Resolves AP-22.

**Before**

```javascript
console.log(`Processing card ${cc} with key ${config.paymentGatewayKey}`);
```

Leaks the card number and gateway key to anywhere that collects stdout.

**After**

```javascript
logger.info('checkout.payment.attempt', {
    userId,
    courseId,
    cardLast4: card.slice(-4),        // never the full number
    amount: course.price,
});
```

Rules: an appropriate level (`debug`/`info`/`warn`/`error`), structured
fields instead of a concatenated string, and no sensitive data — cards become
last four digits, passwords and tokens never appear, emails only with a legal
basis.

---

## Recommended order of application

1. RP-01 (config) — enables the rest
2. RP-02 (parameterize queries) — security, local and cheap change
3. RP-12 (password hashing) and removing sensitive fields from serializers
4. RP-03 (split the God Module) — the big structural move
5. RP-05 (dependency injection)
6. RP-04 (extract Services)
7. RP-06 (declarative routes)
8. RP-11 (centralized errors) + RP-13 (validation) — these shrink Controllers
9. RP-07, RP-08, RP-09, RP-10 — data and performance fixes
10. RP-14, RP-15, RP-16 — final cleanup

Validate after each block, not only at the end. When 30 files have changed
and the app will not boot, finding the cause costs more than validating along
the way.
