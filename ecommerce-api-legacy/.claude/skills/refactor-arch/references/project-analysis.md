# Project analysis — detection heuristics

Phase 1 knowledge. The goal here is to establish facts, not to judge.
Judgment is Phase 2.

## 1. Language and version

Start with the manifests, not the extensions. The manifest gives you
language, framework and version at once; a file extension only gives you the
language, and it still gets polyglot projects wrong.

| File found | Language | Where the version lives |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python | `python_requires`, `.python-version`, `runtime.txt` |
| `package.json` | Node.js | `engines.node` field |
| `composer.json` | PHP | `require.php` |
| `go.mod` | Go | `go` directive on the first line |
| `Gemfile` | Ruby | `.ruby-version`, `ruby` in the Gemfile |
| `pom.xml`, `build.gradle` | Java | `maven.compiler.source` / `sourceCompatibility` |

If there is no manifest, count the extensions in the source directory and use
the dominant one. Record in the report that detection fell back to
extensions — it is a sign of a poorly packaged project and usually a LOW
finding in its own right.

## 2. Framework

Cross-reference the declared dependency against the entry point import.
Declared but not imported is a dead dependency; imported but not declared is
a phantom dependency. Both are findings.

| Dependency | Framework | Typical entry point |
|---|---|---|
| `flask` | Flask | `app.py`, `wsgi.py`, `main.py` |
| `django` | Django | `manage.py`, `settings.py` |
| `fastapi` | FastAPI | `main.py` |
| `express` | Express | `index.js`, `app.js`, `server.js`, `src/app.js` |
| `@nestjs/core` | NestJS | `main.ts` |
| `koa` | Koa | `app.js` |
| `laravel/framework` | Laravel | `public/index.php` |
| `symfony/*` | Symfony | `public/index.php` |
| `rails` | Rails | `config/application.rb` |
| `gin-gonic/gin`, `labstack/echo` | Gin / Echo | `main.go` |

Micro-frameworks (Flask, Express, Koa, Gin) impose no architecture. That is
where most of the mess in this catalog lives, and also where refactoring to
MVC has the greatest effect. Opinionated frameworks (Django, Rails, Laravel,
NestJS) already ship the layers — there the question is whether the team
followed the convention, not whether the structure exists.

## 3. Database and persistence layer

Determine three things: which database, how the code talks to it, and which
tables exist.

**Driver and approach:**

| Signal in the code | Approach | Associated risk |
|---|---|---|
| `sqlite3`, `psycopg2`, `mysql.connector`, `pg`, `mysql2` | Raw SQL | injection, if there is concatenation |
| `SQLAlchemy`, `Sequelize`, `Prisma`, `TypeORM`, `Mongoose`, `ActiveRecord` | ORM | N+1, uncontrolled lazy loading |
| `.query(`, `.execute(`, `.raw(` inside an ORM project | hybrid | inconsistent conventions |

**Tables:** look in this order —

1. `CREATE TABLE` in raw SQL or in migration files.
2. ORM model declarations (`class X(db.Model)`, `sequelize.define`,
   `@Entity`), remembering that `__tablename__` may differ from the class
   name.
3. Names referenced in `FROM` and `JOIN` clauses, to catch tables nobody
   declared.

**Where the queries live** is the most important fact in this section.
Queries scattered across controllers and routes is the primary symptom of a
missing data layer — and it defines much of the Phase 3 work.

## 4. Route inventory

This inventory is the regression contract. Capture method, path and handler
for every route before touching anything.

Patterns per framework:

- **Flask** — `@app.route(...)` and `@bp.route(...)` decorators, plus
  `app.add_url_rule(path, endpoint, handler, methods=[...])`. `add_url_rule`
  is easy to miss on a quick read and often concentrates the routes of
  projects without blueprints.
- **Express** — `app.get/post/put/patch/delete`, `router.<method>`, and
  routes registered inside class methods (look for `setupRoutes`,
  `registerRoutes`, `init`). Also assemble the prefixes from
  `app.use('/api', ...)`.
- **Django** — `urlpatterns` in `urls.py`, including nested `include()`.
- **Laravel** — `routes/web.php` and `routes/api.php`.
- **Rails** — `config/routes.rb`.

Note administrative routes separately (`/admin/*`, `/internal/*`,
`/debug/*`). They tend to be the most dangerous and the least protected.

Watch the ordering: in nearly every router, the first matching route wins.
`/products/search` declared after `/products/<id>` is never reached if the
parameter accepts strings. Preserve the relative ordering in Phase 3.

## 5. Domain

Describe what the system does, in one line. The clues, in order of
reliability:

1. Table names (`products`, `orders`, `order_items` → e-commerce;
   `courses`, `enrollments`, `payments` → learning platform;
   `tasks`, `categories` → task manager).
2. Route paths.
3. The project README — useful, but check it against the code. READMEs lie
   often, because they age faster than the code.
4. Directory and package name — the least reliable clue of all. A directory
   named `ecommerce-api-legacy` may perfectly well contain a courses API.

## 6. Architecture level

Classify into one of three. The level defines the scope of Phase 3.

**Monolithic** — everything in a handful of files at the root, with no layer
directories. Routes, business rules and SQL coexist in the same file,
sometimes in the same function. Symptoms: a file over 250 lines covering
different domains; an entry point that does setup, routing and logic.
→ Phase 3 restructures everything.

**Partially separated** — directories exist (`models/`, `routes/`, `utils/`)
but responsibilities leak between them. Symptoms: routes with 80 lines of
business logic; `utils/` becoming the dumping ground for whatever did not fit
elsewhere; anemic models that only declare columns; serialization duplicated
in every handler.
→ Phase 3 introduces the missing layer and moves logic, preserving what
already works.

**Layered** — real and consistent separation, with dependency injection and
respected boundaries. Symptoms that you are here: controllers do not import
database drivers; business rules are testable without booting an HTTP server.
→ Phase 3 fixes only the individual findings. Do not restructure what is
already in place.

## 7. File count

Count only application source code. Excluded: dependencies
(`node_modules/`, `.venv/`, `vendor/`), build artifacts, lock files,
generated migrations, `__pycache__`, `.git`.

The number goes into the `Source files` field of the summary and must match
reality — it is the one figure a reviewer can verify in two seconds, and
getting it wrong costs credibility for the entire report.
