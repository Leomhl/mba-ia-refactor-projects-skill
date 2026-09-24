---
name: refactor-arch
description: Audits and refactors a backend project to the MVC pattern. Detects the stack automatically (Python/Flask, Node/Express, PHP, Ruby, Go), cross-references the code against a severity-classified anti-pattern catalog, emits an audit report with exact file and line numbers and — after human confirmation — restructures the project into layers and validates that the application still responds. Use when asked for an architecture audit, MVC refactoring, code smell analysis, or technical debt assessment of a legacy project.
---

# refactor-arch

Architectural refactoring in three phases. Each phase has an input, an output
and an exit gate. Do not skip phases and do not merge two phases into a
single response.

The flow is deliberately sequential because each phase depends on facts
established by the previous one: you cannot classify severity without knowing
the framework, and you cannot refactor without knowing what is broken.

## Non-negotiable rules

1. **Phases 1 and 2 are read-only.** No project file may be created, moved or
   edited before explicit user confirmation at the end of Phase 2.
2. **Every finding cites file and line.** `models.py:110` is actionable,
   "the models have problems" is not. If you cannot cite the line, the
   finding is not ready for the report.
3. **No endpoint may disappear during refactoring.** The route inventory from
   Phase 1 is a contract. Same URL, same method, same response shape, same
   status code.
4. **Refactoring without validation does not count as done.** If the app does
   not boot or an endpoint regresses, fix it before reporting Phase 3.

## Phase 1 — Analysis

Goal: find out what you are dealing with, without judging yet.

Read `references/project-analysis.md` and follow the detection heuristics.
The short version:

1. Identify the language from manifest files (`requirements.txt`,
   `package.json`, `composer.json`, `go.mod`, `Gemfile`) before looking at
   file extensions — the manifest also gives you the versions.
2. Identify the framework and version from declared dependencies, and confirm
   it against the entry point imports.
3. Map the database: driver in use, ORM or raw SQL, table names.
4. **Read every source file in the project, start to finish.** This is the
   only phase where you have license to read everything; Phase 2 depends on
   you holding the whole codebase in your head. Small projects (< 3000 lines)
   must be read in full, not sampled.
5. Build the route inventory: HTTP method, path and handler for each one.
   Keep this list — it becomes the regression contract for Phase 3.
6. Classify the current architecture into one of the levels described in the
   reference file (monolithic, partially separated, layered).

Print the summary in exactly this format:

```
==================================
PHASE 1: PROJECT ANALYSIS
==================================
Language:      <language + version when detectable>
Framework:     <framework + version>
Dependencies:  <relevant libraries, comma separated>
Domain:        <what the application does, in one line>
Architecture:  <level + short justification>
Source files:  <N> files analyzed
Endpoints:     <N> routes mapped
DB tables:     <tables, comma separated>
==================================
```

The `Domain` field is what separates a real analysis from an extension check:
describe the business ("e-commerce API with products, orders and checkout"),
not the technology.

## Phase 2 — Audit

Goal: turn reading into classified, actionable findings.

Read `references/anti-patterns.md` and sweep the code against every catalog
entry. For each anti-pattern the file provides concrete detection signals —
look for the signal, not the vibe.

Sweep priority, in this order:

1. Security (credentials, SQL injection, data leaks, weak cryptography) —
   almost always CRITICAL and what the user most needs to know.
2. Layer violations (God Class, business logic inside Controller/route,
   database access inside a View).
3. Data integrity (missing transactions, deletes without cascade, race
   conditions).
4. Performance (N+1, queries inside loops, missing pagination).
5. Consistency and readability (duplication, magic numbers, poor naming).

Classification rules:

- Severity comes from the table in `references/anti-patterns.md`, but may go
  up one level when context makes it worse (SQL injection on a public login
  route is worse than in an internal script). If you raise or lower a level,
  say why in the `Impact` field.
- Identical findings repeated across several places become **one** finding
  listing every occurrence. Twenty lines of SQL concatenation are one
  problem, not twenty.
- Minimum of 5 findings, of which at least 1 is CRITICAL or HIGH. If you
  found fewer than that in a legacy project, you did not read the code
  carefully enough — go back and reread with the catalog open beside you.

Write the report following `references/report-template.md`, without inventing
new sections and without omitting existing ones. Always order CRITICAL →
HIGH → MEDIUM → LOW.

Print the report and **stop**. Ask:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Wait for the answer. A "no" ends the skill with the report delivered — which
is a legitimate outcome, not a failure. Do not start Phase 3 on your own
initiative, nor "just to get ahead".

## Phase 3 — Refactoring

Goal: apply the fixes and prove the application survives.

Read `references/mvc-guidelines.md` (target architecture) and
`references/refactoring-playbook.md` (how to transform each anti-pattern).

Calibrate the effort by the architecture level detected in Phase 1:

- **Monolithic** — full restructuring: create the layers from scratch, split
  the god files by domain, extract configuration, centralize error handling.
- **Partially separated** — the folder structure exists but responsibilities
  leak. Introduce the missing layer (usually Controllers or Repositories),
  move logic to the right place and preserve module names that already work.
  Do not rename folders out of personal taste.
- **Layered** — fix only the individual findings. Restructuring a project
  that is already organized is damage, not improvement.

Execution order that minimizes risk:

1. Extract configuration into its own module reading environment variables.
   Create `.env.example`. Never commit a real secret.
2. Create the target directory tree (models, views/routes, controllers,
   services when there is genuine business logic, middlewares, config).
3. Move data access into Models/Repositories, **parameterizing every query**
   along the way.
4. Move business rules out of Controllers into Services (or into Models, for
   simple domains). The Controller becomes an orchestrator: receive,
   delegate, respond.
5. Reduce routes to pure declaration: path, method, middleware, handler.
6. Centralize error handling and input validation.
7. Rewrite the entry point as a composition root: it only wires and boots.
8. Remove the old files left orphaned. Leaving an empty `controllers.py`
   next to `controllers/` confuses whoever arrives next.

Every transformation has a ready-made pattern in the playbook. Use them —
they already handle the edge cases (static vs. dynamic route ordering,
callback hell, ORM transactions).

### Validation (mandatory)

Not optional, and not "the user will test it later":

1. Boot the application. It must start with no errors and no new warnings.
2. Exercise **every** endpoint from the Phase 1 inventory — not a sample.
   `curl` with status code checking covers most cases.
3. Compare response bodies against the original behavior on endpoints that
   return data. A 200 with different JSON is a silent regression.
4. If any endpoint regressed, fix it and run everything again. Only report
   success when the whole battery passes.

One detail that saves time: if the default port is taken (on macOS, the
AirPlay Receiver listens on 5000), the configuration extracted in step 1
already lets you boot on another port via environment variable. Use that
instead of editing code to test.

Print the closing summary:

```
==================================
PHASE 3: REFACTORING COMPLETE
==================================
## New Project Structure
<resulting directory tree>

## Findings Resolved
<N of M findings fixed; explicitly list the unfixed ones and why>

## Validation
  [ok] Application boots without errors
  [ok] <N>/<N> endpoints respond correctly
  [ok] Zero anti-patterns remaining from the audit
==================================
```

If any finding was left out — because it requires a product decision, depends
on external infrastructure, or is too risky for the scope — declare it
instead of staying silent. An honest report is worth more than a green
checklist.

## Reference files

| File | When to read |
|---|---|
| `references/project-analysis.md` | Phase 1, before detecting the stack |
| `references/anti-patterns.md` | Phase 2, during the sweep |
| `references/report-template.md` | Phase 2, when writing the report |
| `references/mvc-guidelines.md` | Phase 3, before creating the structure |
| `references/refactoring-playbook.md` | Phase 3, for each transformation |

Read them on demand, in the matching phase. Loading all five at once fills
the context with knowledge you cannot use yet.
