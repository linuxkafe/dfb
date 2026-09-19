---
ticket: T008
title: Decision engine with real telemetry (state estimation + advisory)
sprint: sprint-02
priority: high
status: pending
created: 2026-09-19
---

# T008 — Decision Engine with Real Telemetry

## Acceptance Criteria

1. **State estimation**: Fuses MAVLink telemetry (attitude, position, velocity) into consistent state estimate (EKF or complementary filter)
2. **Advisory decisions**: `/decide` endpoint uses real telemetry + mission goal to output safe advisory (heading, altitude, speed)
3. **Safety envelope**: Decisions respect geofence, altitude limits, battery reserve, link quality
4. **Mode awareness**: Respects FC flight mode (MANUAL, STABILIZE, AUTO, RTL, etc.) — only advises in compatible modes
5. **Client integration**: `dfb decide --telemetry` uses live state from Deck
6. **Tests**: Unit tests for state estimator, safety envelope, decision logic with mocked telemetry

## Scope

- **In**: State estimation (complementary filter), advisory decision logic, safety envelope, mode checking, updated `/decide` API
- **Out**: Low-level control (FC remains authority), CRSF (T010), gRPC (T011)

## Dependencies

- T007 (MAVLink telemetry ingestion)
- numpy (already in deps)
- filterpy or custom EKF (evaluate)

## References

- docs/REQUIREMENTS.md REQ-11
- src/dfb/cpu_engine.py (existing MLP)
- src/dfb/mavlink_ingest.py (T007)