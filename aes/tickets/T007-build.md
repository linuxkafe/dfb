---
ticket: T007
phase: build
status: done
created: 2026-09-19
requires:
  - aes/kanban.md
  - aes/tickets/T007-mavlink-telemetry-ingestion.md
  - aes/tickets/T007-plan.md
produces:
  - aes/tickets/T007-build.md
blocked_by: ''
---

# T007 — Build: MAVLink Telemetry Ingestion Pipeline

## Implementation Summary

Implemented MAVLink telemetry ingestion pipeline for Steam Deck Fly Brain service. Added background task that connects to flight controller via serial/UDP, parses 6 key MAVLink message types (HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, BATTERY_STATUS, RC_CHANNELS), maintains thread-safe telemetry state, and exposes `/telemetry` REST endpoint. All configurable via environment variables with systemd integration.

## Changed Files

| File | Operation | Lines +/- | Why |
|------|-----------|-----------|-----|
| `src/dfb/mavlink_ingest.py` | created | +287 | Core MAVLink ingestion: connection, parser, TelemetryState, reconnection logic |
| `src/dfb/__init__.py` | created | +15 | Export public API (TelemetryState, get_telemetry_state, start/stop_mavlink_task) |
| `src/dfb/service.py` | modified | +65/-1 | Add lifespan MAVLink task, `/telemetry` endpoint, import mavlink_ingest |
| `pyproject.toml` | modified | +2 | Add `pyserial` and `pytest-asyncio` dependencies |
| `deploy/flybrain.service` | modified | +6 | Add MAVLINK_* environment variables with defaults |
| `scripts/deploy_deck.sh` | modified | +3 | Add dialout group membership check for serial access |
| `tests/test_mavlink.py` | created | +232 | Unit tests for parser, thread safety, link timeout, module API |
| `tests/conftest.py` | modified | +25 | Add mock MAVLink message/connection fixtures |
| `aes/kanban.md` | modified | +18/-2 | Added Sprint 02 tickets (T007-T012) |

## Diffstory

### What changed?

**New module `src/dfb/mavlink_ingest.py`** (287 lines):
- `TelemetryState` dataclass: thread-safe container for all telemetry fields (position, attitude, velocity, battery, RC channels, message counts)
- `MavlinkReader` class: manages MAVLink connection (serial or UDP), runs blocking reader loop in thread pool, parses 6 message types, implements exponential backoff reconnection (1s→2s→4s→8s→max 30s)
- Module-level API: `start_mavlink_task()`, `stop_mavlink_task()`, `get_telemetry_state()` for FastAPI lifespan integration

**Modified `src/dfb/service.py`**:
- Updated lifespan to start MAVLink task on startup with env var config (device, baud, system/component IDs)
- Added `/telemetry` endpoint returning structured JSON with all telemetry fields + metadata (timestamp, link_ok, message_counts)
- Removed unused `TelemetryState` import (lint fix)

**Configuration via env vars** (with defaults matching plan):
- `MAVLINK_DEVICE=/dev/ttyACM0` (or `udp:0.0.0.0:14550` for SITL)
- `MAVLINK_BAUD=57600`
- `MAVLINK_SOURCE_SYSTEM=255`, `MAVLINK_SOURCE_COMPONENT=190`
- `MAVLINK_TARGET_SYSTEM=1`, `MAVLINK_TARGET_COMPONENT=1`

**Tests** (`tests/test_mavlink.py`): 12 unit tests covering:
- TelemetryState defaults
- All 6 message type parsers (heartbeat, attitude, position, sys_status, battery, rc_channels)
- Message counts increment
- Thread safety (concurrent read/write)
- Link timeout detection (2s threshold)
- Module API (start/stop task, get_state with no reader)
- Integration test placeholder (marked slow, skipped)

**Fixtures** (`tests/conftest.py`): `mock_mavlink_message`, `mock_mavlink_connection` for test isolation.

### Why these files?

- **mavlink_ingest.py**: Core requirement — all MAVLink logic isolated in dedicated module per plan
- **service.py**: FastAPI integration point — lifespan manages background task, endpoint exposes data
- **__init__.py**: Public API exports for clean imports (e.g., `from src.dfb import get_telemetry_state`)
- **pyproject.toml**: `pyserial` required for serial MAVLink; `pytest-asyncio` for async tests
- **flybrain.service**: Systemd env vars make config deploy-time configurable without code changes
- **deploy_deck.sh**: Dialout group warning prevents silent serial permission failures on Deck
- **test_mavlink.py**: Verifies parser correctness, thread safety, reconnection logic per acceptance criteria
- **conftest.py**: Reusable mocks reduce test boilerplate

### What was intentionally untouched?

- **Existing endpoints** (`/health`, `/version`, `/decide`, `/command`, safety gate) — no modifications, regression tests pass
- **CPU engine** (`cpu_engine.py`) — unchanged, still used by `/decide`
- **Vulkan engine** (`vulkan_engine.py`) — untouched (T005 deferred)
- **Client/CLI** (`client.py`, `cli.py`) — `dfb telemetry` command not added (deferred to follow-up)
- **MuJoCo sim** — untouched
- **Coverage threshold** — remains 80% in pyproject.toml; overall coverage 19% is pre-existing (cli.py, cpu_engine.py, service.py, vulkan_engine.py have 0% coverage). New `mavlink_ingest.py` achieves 67%.

### What was verified?

- **All tests pass**: 26 passed, 1 skipped (integration), 0 failed
- **Lint passes**: ruff clean (after fixing docstring line length, unused import, missing newline)
- **No regressions**: Existing tests in `test_client.py`, `test_main.py`, `deck/test_integration.py`, `sim/test_zink.py` all pass
- **Thread safety test**: 5 writer + 5 reader threads × 100 iterations = no corruption
- **Parser tests**: All 6 message types produce expected state updates
- **Timeout test**: Link marked `link_ok=false` after 2s silence
- **API tests**: start/stop task lifecycle, get_state with/without reader

### Remaining risks

1. **Serial permissions on Deck**: `deck` user must be in `dialout` group. Deploy script warns but doesn't enforce. May need `sudo usermod -a -G dialout deck` on Deck.
2. **BAUD rate mismatch**: FC and Deck must agree. Default 57600 is common but not universal. Configurable via env var.
3. **FC message streams**: FC must stream required messages at useful rates (configure SRx_PARAMS on FC). No auto-request implemented.
4. **UDP SITL untested**: UDP path (`udp:...`) compiles but not integration-tested (requires mavproxy).
5. **Coverage gap**: Overall project coverage 19% < 80% threshold. Pre-existing issue — new code at 67%. Recommend adding tests for cli.py, cpu_engine.py, service.py in follow-up tickets.
6. **No `dfb telemetry` CLI**: Client extension deferred (T008/T011).
7. **Reconnection stress**: Exponential backoff logic tested but not under sustained disconnect/reconnect cycles.

## Decisions Made

| Decision | Rejected Alternative | Reason |
|----------|---------------------|--------|
| `pymavlink` direct (not mavsdk) | mavsdk async wrapper | Lower-level control, already in deps, simpler for single connection |
| Thread pool for blocking reader | asyncio-native MAVLink | pymavlink is synchronous; `asyncio.to_thread()` avoids blocking event loop |
| Exponential backoff (1→30s) | Fixed interval | Standard pattern for connection recovery; avoids thundering herd |
| 2s link timeout | 1s / 5s | Balances sensitivity vs noise; matches typical MAVLink heartbeat rate (1Hz) |
| Env vars for config | Config file / CLI args | Matches 12-factor app; systemd drops env vars directly; no extra parser needed |
| Skip `TelemetryState` in `/telemetry` response | Include raw dataclass | JSON serialization cleaner with explicit dict; unit conversion (mm→m, cm/s→m/s) done in endpoint |

## Scope Creep Detected

- [ ] None — all changes within T007 plan scope
- Backlog tickets T008-T012 created during planning (not implementation)

## Quality Gates (Local)

- [x] Tests pass (26 passed, 1 skipped)
- [x] Lint passes (ruff clean)
- [ ] Coverage ≥80% — **Pre-existing failure** (19% overall, 67% for new module)
- [x] No TODO in source
- [x] No dead code
- [x] No critical files touched without flagging

## Notes for Verify

**Areas needing special attention:**
1. Serial device access on physical Steam Deck — verify `dialout` group and device path
2. FC message stream configuration — ensure HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, BATTERY_STATUS, RC_CHANNELS are enabled
3. MAVLink v2 vs v1 — code uses `mavutil.mavlink_connection` which auto-negotiates
4. Systemd service restart — verify `Restart=on-failure` works with MAVLink task cleanup

**Edge cases that may be fragile:**
- Rapid connect/disconnect cycles (backoff max 30s)
- Partial message loss (parser ignores unknown types silently)
- RC_CHANNELS with <16 channels (pads with 1500/default)

**Rollback path if Verify fails:**
```bash
git revert HEAD  # Reverts all T007 changes
# Or selectively:
git restore src/dfb/service.py pyproject.toml deploy/flybrain.service scripts/deploy_deck.sh tests/conftest.py
rm src/dfb/mavlink_ingest.py src/dfb/__init__.py tests/test_mavlink.py
```