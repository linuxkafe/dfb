# Quality Gates

Base gates run via `make check`. Extend this file with domain-specific gates.

## Base Gates (All Projects)

| Gate | Command | Failure Action |
|------|---------|----------------|
| Docs check | `make docs-check` | BLOCKER — docs missing or stale |
| Code check | `make code-check` | BLOCKER — TODOs or structure issues |
| Test check | `make test-check` | WARNING — coverage below threshold |
| Lint check | `make lint-check` | BLOCKER — lint errors |
| Premise check | `make premise-check` | BLOCKER — premise propagation failure |

## Adding Domain Gates

Add sections below for frontend, backend, infrastructure, or custom gates.
