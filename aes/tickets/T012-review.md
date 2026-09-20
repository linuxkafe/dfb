---
ticket: T012
phase: review
status: done
created: 2026-09-20
---

# T012 — Review: Safety Certification Artifacts

## Findings (all resolved in build)

| # | Severity | Finding | Closure |
|---|----------|---------|---------|
| 1 | **BLOCKER** | Traceability matrix and safety case cited test evidence at non-existent paths (`test_safety.py::test_altitude_floor`, `test_health_endpoint`). Phantom references = fabricated evidence for a safety artifact. | Rewrote matrix against real pytest nodes (`tests/test_advisor.py::TestSafetyEnvelope::...`, `test_health.py::TestWatchdog::test_watchdog_detects_stale_link`, etc.). Gate now resolves every referenced file+node. |
| 2 | **MAJOR** | `make safety-check` was decorative: it printed PASS unconditionally, parsing no content. | Rewired to `scripts/safety_check.py` → `docs/safety/traceability.py::check_traceability()`; gate fails on orphan/unknown/missing-ref. |
| 3 | **MAJOR** | Gate hazard set (FC-01..40) diverged from FHA (FC-01..46); duplicate dict keys silently collapsed entries. | Single HAZARDS set mirrors FHA exactly; duplicates removed; 5 non-automated hazards explicitly justified in `N_A_TESTS`. |
| 4 | **MAJOR** | `docs/REQUIREMENTS.md` had no numbered requirement baseline, so REQ-01..20 in the matrix were unverifiable. | Rewrote REQUIREMENTS.md as REQ-01..REQ-20 baseline aligned with the matrix keys. |
| 5 | **MINOR** | `case.md` duplicate evidence numbers and wrong class prefixes. | Renumbered E2.x/E3.x/E4.x; corrected to `Class::test` paths. |
| 6 | **MINOR** | `emergency.md` duplicate section headers (two `#5`, four `#6`). | Reconciled to 7 distinct scenarios incl. DFB power loss / overheating / kill switch. |

## Acceptance criteria verdict

| Criterion | Verdict |
|-----------|---------|
| SSA documents system/env/safety requirements | ✅ `ssa.md` |
| FHA ≥10 failure conditions with severity | ✅ 46 FCs, 5 severity classes |
| FTA ≥4 top events with minimal cut sets | ✅ 4 TEs, cut-set tables, CCF |
| Traceability matrix REQ→Hazard→Test | ✅ validated by `make safety-check` |
| Safety case (GSN) residual-risk argument | ✅ `case.md`, 5 sub-goals, 34 evidence items |
| Operational limits with configurable parameters | ✅ 7 parameter tables |
| Emergency procedures ≥6 scenarios | ✅ 7 scenarios + checklists |
| CI gate `make safety-check` passes | ✅ added to `.github/workflows/ci.yml` |

## Open gaps (accepted, tracked)

- **FC-41** — CRSF watchdog task test not yet implemented (documented N/A). Requires a unit test against crsf ingest watchdog timing.
- **HTTP route coverage** — `service.py` endpoint logic has no direct tests (only component-level). Pre-existing, see coverage.xml.
- Gate guarantees reference *existence*, not *semantic* adequacy (a test covered "somehow"). Semantic review remains a weekly manual check.