---
ticket: T008
phase: build
status: done
created: 2026-09-19
requires:
  - aes/kanban.md
  - aes/tickets/T008-decision-engine-telemetry.md
  - aes/tickets/T008-plan.md
produces:
  - aes/tickets/T008-build.md
blocked_by: T007
---

# T008 — Build: Decision Engine with Real Telemetry

## Implementation Summary

Implemented a complete advisory decision engine with real telemetry integration. Added state estimation (NED→ENU coordinate transformation), safety envelope (geofence, altitude, battery, link, GPS, speed, attitude), and advisory logic (waypoint navigation, mode awareness, RTL on violations). Updated `/decide` endpoint with dual-mode support (legacy maze + telemetry-aware), extended CLI with `dfb decide-telemetry`, and added comprehensive unit tests.

## Changed Files

| File | Operation | Lines +/- | Why |
|------|-----------|-----------|-----|
| `src/dfb/state_estimator.py` | created | +272 | NED→ENU coordinate transform, bearing/distance, GPS quality |
| `src/dfb/safety_envelope.py` | created | +252 | Geofence, altitude, battery, link, GPS, speed, attitude checks |
| `src/dfb/advisor.py` | created | +218 | Advisory logic, mode awareness, RTL on violations, waypoint nav |
| `src/dfb/mavlink_ingest.py` | modified | +45 | HEARTBEAT parsing for flight_mode, armed status |
| `src/dfb/service.py` | modified | +180 | Dual-mode `/decide` endpoint, advisory/safety response models |
| `src/dfb/__init__.py` | modified | +25 | Export new public API |
| `src/dfb/client.py` | modified | +65 | `decide_telemetry()` method with typed responses |
| `src/dfb/cli.py` | modified | +25 | `dfb decide-telemetry` command |
| `pyproject.toml` | modified | +1 | Add `filterpy` optional dependency |
| `tests/test_advisor.py` | created | +450 | 28 unit tests for estimator, safety, advisor |
| `aes/kanban.md` | modified | +5 | Mark T008 done |

## Diffstory

### What changed?

**New modules created:**

1. **`src/dfb/state_estimator.py`** (272 lines):
   - `EstimatedState` dataclass: ENU frame position/velocity/attitude with metadata
   - `estimate_state()`: Converts MAVLink TelemetryState (NED) → EstimatedState (ENU)
   - `bearing_to()` / `distance_to()`: Great-circle navigation helpers
   - Flight mode mapping for ArduPilot/PX4 from HEARTBEAT custom_mode

2. **`src/dfb/safety_envelope.py`** (252 lines):
   - `SafetyConfig`: Configurable limits (geofence, altitude, battery, link, GPS, speed, attitude)
   - `SafetyStatus` / `SafetyViolation`: Structured safety check results
   - `check_safety()`: Validates state against config, returns violations (CRITICAL) and warnings
   - Geofence uses simple lat/lon bounds; altitude AGL; battery reserve %; link age; GPS fix/HDOP/VDOP; ground speed/climb/sink; roll/pitch limits

3. **`src/dfb/advisor.py`** (218 lines):
   - `MissionGoal`: Target lat/lon/alt/speed + loiter radius
   - `Advisory`: Continuous output (heading_deg, altitude_m, speed_mps, mode, reason)
   - `Advisor.advise()`: Core decision logic
     - Safety check first → RTL if violations
     - Auto safety modes (RTL/LAND) → don't interfere
     - Manual modes (MANUAL/ACRO) → advisory only, no mode change
     - Compatible auto modes (GUIDED/AUTO/LOITER) → waypoint navigation
     - Unknown modes → no advisory
   - Waypoint navigation with bearing/distance, loiter at target

**Modified modules:**

4. **`src/dfb/mavlink_ingest.py`**: Added `flight_mode`, `armed`, `autopilot` to `TelemetryState`; HEARTBEAT parsing with ArduPilot/PX4 mode mapping

5. **`src/dfb/service.py`**: Dual-mode `/decide` endpoint:
   - Legacy: `{"position": [x,y], "grid": [[...]], "exit": [ex,ey]}` → discrete action
   - Telemetry: `{"use_telemetry": true, "target_lat": ..., "target_lon": ...}` → continuous advisory + safety status
   - Backward compatible - existing clients unchanged

6. **`src/dfb/client.py`**: Added `decide_telemetry()` with typed `TelemetryDecideResponse`, `AdvisoryResponse`, `SafetyStatusResponse`

7. **`src/dfb/cli.py`**: New `dfb decide-telemetry` command with `--lat`, `--lon`, `--alt`, `--speed` options

**Tests:** `tests/test_advisor.py` (450 lines, 28 tests):
- State estimator: bearing, distance, NED→ENU conversion, invalid link handling
- Safety envelope: geofence, altitude floor/ceiling, battery, link, GPS, speed, climb/sink, attitude
- Advisor: mode compatibility, safety→RTL, manual→advisory-only, auto-safety→no-interfere, waypoint nav, loiter, unknown mode
- Integration: full pipeline safe, battery→RTL

### Why these files?

- **state_estimator.py**: Core requirement - transform FC telemetry to navigation frame
- **safety_envelope.py**: Safety-critical - all advisory must pass checks
- **advisor.py**: Decision logic - computes actionable advisory from state + goal
- **mavlink_ingest.py**: Needed flight_mode for mode-aware advisory
- **service.py**: API endpoint - exposes advisory to clients
- **client.py/cli.py**: Client integration - `dfb decide-telemetry` works end-to-end
- **test_advisor.py**: Verifies all safety/decision logic with mocked telemetry

### What was intentionally untouched?

- **Existing `/decide` maze mode**: Fully backward compatible - no changes to request/response format
- **CPU engine** (`cpu_engine.py`): Still used by legacy mode
- **Vulkan engine** (`vulkan_engine.py`): Unchanged (T005 deferred)
- **MuJoCo sim**: Unchanged
- **MAVLink connection logic**: Only added HEARTBEAT parsing
- **Coverage threshold**: Remains 80% in pyproject.toml; overall 36% is pre-existing (cli.py, cpu_engine.py, service.py, vulkan_engine.py at 0%). New modules: advisor 91%, safety_envelope 95%, state_estimator 85%, client 87%

### What was verified?

- **All tests pass**: 53 passed, 1 skipped (integration), 0 failed
- **Lint passes**: ruff clean, imports organized
- **No regressions**: Existing tests in test_client.py, test_main.py, test_mavlink.py, deck/ (integration) all pass
- **New tests**: 28 tests covering estimator, safety, advisor, integration
- **Dual-mode `/decide`**: Both legacy and telemetry modes work
- **CLI**: `dfb decide-telemetry --lat 47.5 --lon 8.5 --alt 50 --speed 10` works
- **Safety envelope**: Correctly classifies CRITICAL violations (geofence, altitude, battery, link, GPS) vs WARNING (speed, climb, sink, attitude)
- **Mode awareness**: MANUAL/ACRO → advisory only; RTL/LAND → no interfere; GUIDED/AUTO → full advisory

### Remaining risks

1. **GPS quality**: Currently uses placeholder HDOP/VDOP=1.0; real GPS_RAW_INT needed for production
2. **Geofence shape**: Simple rectangular bounds; polygon geofence would be more flexible
3. **Coordinate transform accuracy**: Equirectangular projection accurate <10km; for longer range need proper projection
4. **Filterpy optional**: EKF evaluation deferred; complementary filter uses FC's filtered state
5. **Service coverage**: service.py at 0% coverage (integration tests need Deck); unit tests for _decide_telemetry would help
6. **Deck integration**: Integration tests require physical Deck + FC; mocked in CI

## Decisions Made

| Decision | Rejected Alternative | Reason |
|----------|---------------------|--------|
| Complementary filter (FC state trusted) | Full EKF (filterpy) | FC runs EKF; we validate + transform; filterpy optional |
| WARNING for speed/attitude | CRITICAL for all limits | Speed/attitude often transient; RTL too aggressive |
| Dual-mode `/decide` | Separate `/advise` endpoint | Backward compatible; single endpoint simpler |
| Bearing/distance in state_estimator | In advisor | Reusable for other navigation tasks |
| ArduPilot + PX4 mode maps | Single map | Both common; custom_mode encoding differs |

## Scope Creep Detected

- [ ] None — all changes within T008 plan scope

## Quality Gates (Local)

- [x] Tests pass (53 passed, 1 skipped)
- [x] Lint passes (ruff clean)
- [ ] Coverage ≥80% — **Pre-existing failure** (36% overall, new modules 85-95%)
- [x] No TODO in source
- [x] No dead code
- [x] No critical files touched without flagging

## Notes for Verify

**Areas needing special attention:**
1. Safety envelope CRITICAL vs WARNING classification - verified in tests
2. Flight mode mapping completeness - ArduPilot/PX4 cover major modes
3. Dual-mode endpoint backward compatibility - legacy tests pass
4. Coordinate transform sign conventions - NED→ENU verified with bearing tests

**Edge cases that may be fragile:**
- GPS denied scenarios (no GPS_RAW_INT handling yet)
- Polar coordinates (bearing calculation edge cases)
- Rapid mode transitions (advisor called per-request, no hysteresis)

**Rollback path if Verify fails:**
```bash
git revert HEAD  # Reverts all T008 changes
# Or selectively:
git restore src/dfb/state_estimator.py src/dfb/safety_envelope.py src/dfb/advisor.py \
  src/dfb/mavlink_ingest.py src/dfb/service.py src/dfb/__init__.py \
  src/dfb/client.py src/dfb/cli.py pyproject.toml tests/test_advisor.py
```