# Quality Gates

Base gates run via `make check`. Extend this file with domain-specific gates.

## Base Gates (All Projects)

| Gate | Command | Failure Action |
|------|---------|----------------|
| Docs check | `make docs-check` | BLOCKER — docs missing or stale |
| Code check | `make code-check` | BLOCKER — TODOs or structure issues |
| Test check | `make test-check` | WARNING — coverage below threshold |
| Lint check | `make lint-check` | BLOCKER — lint errors |
| Tautology check | `make tautology-check` | BLOCKER — always-true/always-false assertion |
| Premise check | `make premise-check` | BLOCKER — premise propagation failure |

## Tautology Gate

Scans `src tests` (same scope as lint) for always-true / always-false
assertion anti-patterns that silently turn tests into no-ops and green
gates into theater — e.g. `assert x or True`. Background: commit `82fe68f`
shipped exactly this class of bug; every gate went green while the
assertion was vacuous.

- **Command:** `make tautology-check` → `python3 scripts/check_tautologies.py`
- **Exit:** 0 = clean, 1 = at least one hit (each printed as
  `file:line:pattern — code`).
- **Self-test:** `python3 scripts/check_tautologies.py --selftest` plants
  one instance of every blacklisted pattern and asserts the gate catches
  them.
- **False positives:** by design the gate flags the line and lets a human
  adjudicate. Do not delete the gate on a controversial hit — rewrite the
  assertion or make the intent explicit. Regex is weaker than semantic AST
  analysis by construction; the gate targets the empirically-occurring
  shapes, not every possible tautology.

## Adding Domain Gates

Add sections below for frontend, backend, infrastructure, or custom gates.
