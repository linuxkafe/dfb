---
sprint: sprint-03
period: 2026-09-19 → 2026-09-20
status: done
---

# Sprint 03 — Comms & Safety

**Goal**: Add CRSF/ELRS support, gRPC API for low latency, and safety certification artifacts.

## Tickets

| ID | Title | Status |
|----|-------|--------|
| T010 | CRSF/ELRS support for crossfire receivers | done |
| T011 | gRPC API for lower-latency client-deck communication | done* |
| T012 | Safety certification artifacts (hazard analysis, test reports) | done |

\* T011 deliverable present but **without committed code or any automated test evidence**
(see retrospective).

## What went well

- T010 delivered 16 CRSF unit tests; unified `/telemetry` with source autodetection.
- T012 produced a full ARP4761-lite artifact set (SSA/FHA/FTA/GSN/gates) with a CI gate
  that validates test-reference existence — the phantom-reference drift was caught and fixed.
- Traceability gate now computes real metrics (20 REQs / 46 hazards / 41 automated / 5 N/A).

## What went wrong

1. **T011 was closed without evidence.** Marked `done` in kanban with **zero tests** in
   `tests/` (confirmed: no `grpc` refs in tests/ or sim/), code never committed, and the
   gRPC command surface is a **safety gate bypass**:
   - `grpc_service.SendCommand` returns `success=True` ("simulated") **without** any
     confirmation token — HTTP `/command` requires one, gRPC does not (REQ-08 violated on
     that transport).
   - `grpc_service.VerifyToken` always returns `valid=False`.
   - `IssueToken` mints tokens the HTTP token store never sees.
   - gRPC server binds `[::]:8083` insecure by default.
   - Net effect: sleeping unauthenticated command surface + broken verification semantics.
2. **Uncommitted evidence trail.** T011 + T012 changes sat uncommitted on top of T010;
   scratch files (`fix_*.py`, `test_*.py`, `proto/`) left at repo root.
3. **Sprint scar tissue**: coverage at 44% across the sprint (cli.py 0%, vulkan_engine 0%,
   grpc 0–30%, service.py 43%, cpu_engine 42%) — only the safety-envelope/health modules
   hit 80%+.

## What to change next sprint

- **No ticket is done without: committed code + test evidence + passing gates** (enforce
  the AES rule "if it's not tested, it's broken" at kanban-close, not by assertion).
- Close the gRPC safety hole **before** adding more surface (see T013).
- Add test evidence for gRPC, HTTP routes, CLI before any transport expands.
- Atomic per-ticket commits; delete/ignore scratch scripts.
- Re-verify FC-41 (CRSF watchdog test) and the 5 N/A hazards before non-experimental use.