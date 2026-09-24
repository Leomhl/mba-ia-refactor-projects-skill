# Audit report template

Phase 2 output format. Use exactly this structure — the report is compared
across projects and across runs, so the format must be stable.

## Structure

```markdown
==================================
ARCHITECTURE AUDIT REPORT
==================================
Project: <directory name>
Stack:   <language + framework>
Files:   <N> analyzed | ~<N> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [SEVERITY] <Anti-pattern name> (<AP-XX>)
File: <path/file.ext>:<line>-<line>
Description: <what is happening in the code, concretely>
Impact: <the practical consequence — what breaks, what leaks, what it costs>
Recommendation: <the fix, referencing the playbook pattern>

[repeat for each finding, ordered CRITICAL → HIGH → MEDIUM → LOW]

==================================
Total: <N> findings
==================================
```

## Filling rules

**File** — always a path relative to the project root, with a line or line
range. Multiple occurrences of the same anti-pattern go into the same
finding, one per line:

```
File: models.py:28, models.py:110, models.py:140, models.py:291
```

Above six occurrences, list the four most representative ones and summarize
the rest: `(+ 9 more occurrences in the same file)`. The report has to stay
readable.

**Description** — describe what the code does, citing the real identifier.
"The `login_user` function builds the query by concatenating `email` and
`password` from the request body" is verifiable. "There are security problems
in the models" is not.

**Impact** — the consequence, not a restatement of the problem. Compare:

- Weak: "This is bad for security."
- Good: "`' OR '1'='1` in the email field authenticates as the first user in
  the table, with no password."

- Weak: "It hurts performance."
- Good: "Listing 100 orders with 3 items each fires 401 queries."

When you change the catalog's base severity, the justification goes here.

**Recommendation** — a concrete action, pointing at the playbook pattern when
one exists: "Parameterize with `?` placeholders and move to
`models/user_model.py` (playbook RP-02)."

## Numbering and ordering

- Order by severity and, within the same level, by perceived impact.
- Cite the catalog ID (`AP-07`) in parentheses in the title. It makes
  finding → fix → validation traceable.
- The `Total` in the footer must match the sum in `Summary`. A mismatch
  between the two is the most common error and the easiest to spot.

## Optional sections

Include only when there is real content:

**`## Deprecated APIs`** — when there are AP-17 findings, a consolidated
table before the detailed findings is worth adding:

```markdown
## Deprecated APIs
| API | Occurrences | Replacement | Severity |
|---|---|---|---|
| `datetime.utcnow()` | 14 | `datetime.now(timezone.utc)` | MEDIUM |
```

**`## Out of scope`** — problems identified that Phase 3 will not solve, with
the reason. Legitimate examples: requires a product decision, depends on an
external service, changes a public contract that would break clients.
Declaring is better than omitting.

## What not to put in the report

- Praise for the code ("despite the problems, the structure is
  interesting"). An audit report is not a peer review.
- Findings without a line number. If you could not find the line, either the
  finding does not exist or the sweep is not finished.
- Style complaints a formatter resolves (quotes, indentation, trailing
  commas). That is not architectural debt.
- Generic recommendations ("apply SOLID", "improve the architecture"). Say
  which principle, in which file, with which transformation.
