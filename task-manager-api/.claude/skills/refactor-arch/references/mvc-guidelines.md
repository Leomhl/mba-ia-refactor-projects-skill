# MVC architecture guidelines

The Phase 3 target architecture. It applies to any language — what changes is
the syntax, not the boundary between layers.

## The layers and what each one may do

### Model — data and data rules

Represents a domain entity and is the only place that talks to the database.

May: declare the entity structure; execute queries; convert a database row
into a domain object; validate the entity's own invariants (non-negative
price, well-formed email); expose controlled serialization.

May not: import anything from the web framework; know about `request` or
`response`; return HTTP status codes; know a Controller exists.

**Boundary test:** if the Model needs an HTTP server running to be tested, it
is not a Model.

With raw SQL, each domain gets its own module (`models/product_model.py`)
holding the access functions. With an ORM, the model class is the layer — but
composed queries belong in it or in a repository, never in the route handler.

### View / Routes — the HTTP edge

In a REST API there are no templates, so the View layer is routing and
serialization. It is the system's public contract.

May: declare path, method and middlewares; point to the Controller; group
routes by resource; define the response format.

May not: contain business rules; access the database; perform domain
calculations.

**Desired shape** — pure declaration, one line per route:

```
GET    /products          → ProductController.list
POST   /products          → ProductController.create
GET    /products/:id      → ProductController.get
```

If the routes file has an `if`, it has left its lane.

**Order matters:** static route before parameterized route.
`/products/search` after `/products/:id` becomes unreachable when the
parameter accepts strings.

### Controller — orchestration

Translates HTTP into a domain call and the result back into HTTP.

May: extract and validate request input; call a Model or Service; map results
to status codes; delegate errors to the central handler.

May not: build SQL; implement business calculations; trigger side effects
(email, queue, webhook) directly — that is a Service's job.

**Target size:** 5 to 15 lines per action. Past 40, there is hidden logic in
there.

Canonical shape:

```
1. extract input
2. validate format (not business rules)
3. delegate to a Service or Model
4. map the result to a status code
5. let errors bubble to the central handler
```

### Service — business rules (when needed)

An optional layer, mandatory when a rule spans entities.

Use it when there is: an operation involving more than one Model (checkout
touches order, item, product and payment); a transaction with multiple
writes; an external integration (gateway, email, queue); a complex domain
calculation (tiered discount, commission, score).

Do not create a Service for simple CRUD. A `ProductService.list()` that only
calls `ProductModel.list()` is an indirection layer with no content — it
costs navigation and delivers nothing.

### Middleware — cross-cutting concerns

Authentication, authorization, error handling, request logging, CORS, rate
limiting, schema validation.

Sign that a middleware is missing: the same `try/except` copied into every
handler.

### Config — environment

A single point that reads environment variables and hands typed values to the
rest of the application. No other file reads `env` directly.

Rules: every secret comes from the environment; an `.env.example` always
exists with keys and sample values (never real ones); `.env` is in
`.gitignore`; safe defaults when a variable is missing — an absent `DEBUG`
means `False`, not `True`.

## Dependency direction

```
Routes → Controllers → Services → Models → Database
                    ↘ Models (when there is no Service)
```

The arrow points one way only. A Model importing a Controller is an inverted
dependency and signals that responsibilities are swapped.

Config and Middleware are cross-cutting: any layer may read Config, and
Middleware acts at the edge.

## Directory structure

The target, adapted to each language's convention:

```
src/
├── config/          # settings read from the environment
├── models/          # one unit per entity
├── controllers/     # one unit per resource
├── services/        # business rules (only when needed)
├── routes/          # route declarations
├── middlewares/     # errors, auth, validation
└── app.*            # composition root
```

**Python/Flask:** `models/product_model.py`,
`controllers/product_controller.py`, routes in `routes/` with blueprints,
`app.py` at the root with an application factory.

**Node/Express:** the same tree under `src/`, with `ProductController.js` or
`product.controller.js` files — pick one convention and stick to it.

**Already partially organized projects:** preserve the folder names that
exist and work. If the project uses `routes/` and `services/`, add
`controllers/` in the same style rather than renaming everything to
`views/`. Refactoring that renames without benefit is noise in the diff and
makes review harder.

## Composition root

The entry point has one responsibility: assemble the application.

Does: load config; instantiate dependencies; register middlewares; register
routes; start the server.

Does not: declare route handlers; contain business rules; define the database
schema.

**Target size:** 20 to 40 lines. Beyond that, it has become the God Module
the refactoring was supposed to eliminate.

## Compliance checklist

Run this at the end of Phase 3:

- [ ] No routes file contains a business-rule `if`
- [ ] No Controller builds a query
- [ ] No Model imports a web framework symbol
- [ ] Every query is parameterized
- [ ] Every secret comes from an environment variable
- [ ] `.env.example` exists and `.env` is gitignored
- [ ] Error handling is centralized, not copied
- [ ] The entry point only composes
- [ ] The original monolithic files were removed, not left orphaned
- [ ] Every route from the Phase 1 inventory still responds
