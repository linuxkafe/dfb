---
ticket: T012
phase: build
status: done
created: 2026-09-20
requires:
  - aes/tickets/T012-plan.md
produces:
  - docs/safety/ssa.md
  - docs/safety/fha.md
  - docs/safety/fta.md
  - docs/safety/traceability.md
  - docs/safety/traceability.py
  - docs/safety/case.md
  - docs/safety/operational_limits.md
  - docs/safety/emergency.md
  - docs/safety/README.md
  - scripts/safety_check.py
  - docs/REQUIREMENTS.md
---

# T012 — Build: Safety Certification Artifacts

## What changed

Created the safety certification package under `docs/safety/` and wired a
real CI gate:

| File | Intent |
|------|--------|
| `docs/safety/ssa.md` | System Safety Assessment: functions, boundaries, interfaces, safety requirements, defense-in-depth architecture, residual risk table |
| `docs/safety/fha.md` | Functional Hazard Analysis: 46 failure conditions (FC-01..FC-46) with severity and mitigation |
| `docs/safety/fta.md` | Fault Tree Analysis: 4 top events (unintended command, link loss undetected, wrong advisory, envelope bypass) with minimal cut sets and CCF |
| `docs/safety/case.md` | GSN-style safety case: 5 sub-goals, 34 evidence items, contextual assumptions, residual-risk statement |
| `docs/safety/operational_limits.md` | Operational envelope with configurable parameters (geofence, altitude, battery, link, GPS, speed, weather) |
| `docs/safety/emergency.md` | 7 emergency procedures + pre-flight checklist + post-incident process |
| `docs/safety/traceability.md` | REQ → Hazard → Test traceability, validated by CI gate |
| `docs/safety/traceability.py` | **Single source of truth** consumed by `make safety-check` |
| `docs/safety/README.md` | Index + maintenance guide |
| `scripts/safety_check.py` | CI gate: validates matrix completeness AND that every referenced test exists |
| `docs/REQUIREMENTS.md` | Numbered REQ-01..REQ-20 baseline the matrix keys off |

## Why it changed

T012 plan called for safety artifacts with CI validation, and specified in its
hostile analysis that the number-one failure mode is **documentation drift**
("artifacts describe v0.1 but code is at v0.5"). The artifacts were drafted but:

1. The first CI gate (`make safety-check`) was decorative — it parsed nothing
   and reported success regardless of content.
2. The traceability matrix cited test evidence that did not exist at the cited
   paths (`test_safety.py::...`, `test_health_endpoint`), i.e. fabricated evidence.
3. The hazard set in the gate (FC-01..40) diverged from the FHA (FC-01..46).
4. `docs/REQUIREMENTS.md` had no numbered requirement baseline for the matrix to
   key off.

Review caught these; build phase then fixed them.

## What was intentionally untouched

- FHA/SSA/FTA/CASE hazard content and severities (analysis work from prior
  drafting). Only references and numbering were corrected.
- No flight/FC integration code was touched; this ticket is documentation +
  gates only.
- Existing tests were neither modified nor renumbered to satisfy the matrix —
  the matrix was rewritten to reference the tests that actually exist.

## Remaining risks

- **TRUTHFUL GAP (by design):** 5 of 46 hazards have no automated test and are
  documented as N/A with justification (CRSF watchdog test planned, OOM/CPU
  config-only, gRPC backpressure). These need new tests before any non-experimental
  use. Tracked in implementation plan (FC-41) and FHA gaps.
- **HTTP endpoint import coverage** still ~0% for `service.py` endpoints; the
  health component logic is tested but not the live HTTP routes. Pre-existing gap,
  not introduced here (see coverage.xml).
- Traceability maintenance is human-dependent for the Markdown rows; the `.py`
  gate prevents reference rot but does not auto-sync tables.

## Verification

- `make test` → 92 passed, 1 skipped (coverage 44% — pre-existing gap in
  `cli.py`, `service.py`, `vulkan_engine.py`, `grpc_*`).
- `make lint` → clean.
- `make safety-check` → OK: 20 REQs, 46 hazards, 41 with automated evidence,
  5 documented non-automated.

## Diffstory

Files added/changed vs. pre-T012-build baseline: 11. No source code under `src/`
was modified. `docs/REQUIREMENTS.md` was rewritten from a 13-bullet checklist into
a numbered REQ-01..20 baseline; the IDs are stable keys used by the gate.