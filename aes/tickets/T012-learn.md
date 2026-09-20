---
ticket: T012
phase: learn
status: done
created: 2026-09-20
---

# T012 — Learn: Safety Certification Artifacts

## Insight 1 — Phantom test references are the classic failure of artifact-driven safety

A safety traceability matrix and GSN safety case quoted `test_safety.py::test_altitude_floor`
and `test_health_endpoint` — **tests that never existed** under those names. The real
safety-envelope tests were in `tests/test_advisor.py::TestSafetyEnvelope`. Nothing caught
this until the matrix was mechanically resolved against the repo.

**Root cause:** artifacts written from an idealized model of the codebase, not from the
codebase itself. Cost of catching late: a reviewer must re-verify every evidence claim.

**Applied:** `make safety-check` now resolves every referenced `tests/...::node` against
the filesystem and fails on any missing file/def. Reference *existence* is enforced;
reference *semantics* still needs human review (noted in T012-review).

## Insight 2 — A gate that always passes is worse than no gate

The original `make safety-check` target used inline Python that imported nothing and
printed "✅ All safety checks passed" unconditionally. It gave false assurance — the exact
"decorative documents" failure mode the T012 plan's hostile analysis predicted.

**Applied:** gate now imports `docs/safety/traceability.py` (single source of truth),
computes completeness metrics (20 REQs / 46 hazards / 41 automated / 5 justified N/A),
reports real numbers, returns non-zero on failure.

## Insight 3 — Requirements need IDs before traceability can exist

A traceability matrix keying on REQ-XX with no numbered baseline in
`docs/REQUIREMENTS.md` is unverifiable. Numbered requirements (REQ-01..20) were added
as the stable key set.

**Process rule going forward:** when starting a ticket whose deliverable claims
traceability, verify the baseline IDs exist before drafting the matrix.

## To-do carried forward

- FC-41 CRSF watchdog unit test (still N/A).
- Direct HTTP route tests for `service.py` (coverage gap).
- Weekly semantic review of traceability: gate checks existence, not adequacy.