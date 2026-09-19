---
ticket: T007
phase: plan
status: done
created: 2026-09-19
tier: standard
requires:
  - aes/kanban.md
  - aes/tickets/T007-mavlink-telemetry-ingestion.md
produces:
  - aes/tickets/T007-plan.md
blocked_by: ''
---

# T007 — Plan: MAVLink Telemetry Ingestion Pipeline

## Reconnaissance Summary

**Existing service structure** (`src/dfb/service.py`):
- FastAPI app with lifespan manager (startup/shutdown)
- Endpoints: `/health`, `/version`, `/decide`, `/confirm/issue`, `/command`, `/confirm/verify/{token}`
- CPU engine initialized in lifespan; thread-safe via module-level singleton
- Safety gate: token-based confirmation for `/command` endpoint
- Runs on Steam Deck via systemd user service (`flybrain.service`)

**Dependencies** (pyproject.toml): `pymavlink` already declared, `pyserial` needed for serial transport

**Deployment**: `scripts/deploy_deck.sh` syncs `src/`, `sim/`, `shaders/`, `pyproject.toml`, `Makefile` to Deck; installs in venv; systemd manages service

**Key files to extend**:
- `src/dfb/service.py` — add MAVLink background task, telemetry state, `/telemetry` endpoint
- `src/dfb/mavlink_ingest.py` — new module for MAVLink connection, parsing, state store
- `src/dfb/__init__.py` — export new public API
- `pyproject.toml` — add `pyserial` dependency
- `tests/test_mavlink.py` — new unit/integration tests

## Hostile Analysis

### ASSUMPTIONS I AM MAKING

- [KNOWN] `pymavlink` is in pyproject.toml — verified
- [KNOWN] Steam Deck has USB/serial ports accessible to user `deck` — standard Linux, user in `dialout` group
- [INFERRED] Flight controller speaks MAVLink v2 over serial (USB/FTDI) at 57600 or 115200 baud — standard ArduPilot/INAV/PX4 config
- [INFERRED] Key messages needed: HEARTBEAT (sys/status), ATTITUDE (roll/pitch/yaw), GLOBAL_POSITION_INT (lat/lon/alt), SYS_STATUS (voltage/current), RC_CHANNELS (pilot input), BATTERY_STATUS — these are standard MAVLink streams
- [ASSUMED] Single MAVLink connection sufficient (no redundant links) — scope of this ticket
- [ASSUMED] Serial device path on Deck: `/dev/ttyACM0` or `/dev/ttyUSB0` — typical for USB telemetry radios or direct FTDI
- [UNKNOWN] Whether FC streams all required messages at useful rates (need to configure SRx_PARAMS on FC)
- [UNKNOWN] Whether SSH tunnel adds latency that affects telemetry freshness — will measure

### WHAT WAS NOT SPECIFIED (that matters)

- Exact serial device path and baud rate (make configurable via env var)
- Whether to support UDP MAVLink (for SITL/testing) alongside serial
- Message rate limits / throttling strategy
- How stale data is represented in `/telemetry` response (timestamp + validity flag)
- Whether to persist telemetry to disk (not needed for MVP)

### ALTERNATIVES NOT CHOSEN

| Option | Reason |
|--------|--------|
| mavsdk (Python) instead of pymavlink | pymavlink is lower-level, more control, already in deps; mavsdk adds async layer we don't need yet |
| Dedicated MAVLink router (mavlink-routerd) | Adds complexity; direct pymavlink in-process is simpler for single connection |
| gRPC streaming for telemetry | Overkill for MVP; REST polling from client is fine at 10-50Hz |

### RISKS AND SIDE EFFECTS

1. **Serial permission issues** on Deck — `deck` user must be in `dialout` group; may need udev rule
2. **BAUD rate mismatch** — FC and Deck must agree; make configurable
3. **Message flooding** — high-rate streams (ATTITUDE @ 50Hz) can overwhelm parser; need rate limiting
4. **Link loss handling** — must not crash service; stale data flag in API response
5. **Thread safety** — MAVLink parsing runs in background thread; state store needs locks
6. **Deploy complexity** — new env vars for serial config must be added to systemd unit

### COST OF BEING WRONG: MEDIUM

- If serial config wrong: service starts but gets no telemetry — detectable via `/telemetry` stale flag
- If parser crashes: background task dies, service still serves `/health` — need watchdog
- If thread safety broken: corrupted state — mitigated by using `threading.Lock` and atomic dataclass swaps

### SCOPE BOUNDARY

**In**: MAVLink v2 serial/UDP connection, message parser for 6 key message types, thread-safe state store, `/telemetry` REST endpoint, auto-reconnect, configurable via env vars

**Out**: CRSF/ELRS (T010), decision logic using telemetry (T008), gRPC streaming (T011), FC parameter management, telemetry persistence

### INVITATION FOR CONTRADICTION

What if the FC doesn't stream BATTERY_STATUS? — fallback to SYS_STATUS voltage/current. What if serial device is `/dev/serial0` (GPIO)? — make device path fully configurable. What if we need multiple MAVLink links (redundancy)? — defer to T008/T010.

## Technical Approach

**Architecture**: Add a background task (asyncio task) in FastAPI lifespan that:
1. Opens MAVLink connection (serial or UDP) using `pymavlink.mavutil.mavlink_connection`
2. Spawns a reader loop (in thread pool via `asyncio.to_thread`) that:
   - Blocks on `recv_match()` with timeout
   - Parses relevant messages
   - Updates thread-safe `TelemetryState` dataclass under lock
3. Implements exponential backoff reconnection on disconnect
4. Exposes `/telemetry` endpoint returning current state + metadata (timestamp, link_status, message_counts)

**Configuration** (env vars):
- `MAVLINK_DEVICE` — serial path (default: `/dev/ttyACM0`) or UDP URL (e.g., `udp:0.0.0.0:14550`)
- `MAVLINK_BAUD` — baud rate (default: `57600`)
- `MAVLINK_SOURCE_SYSTEM` — our system ID (default: `255` for ground station)
- `MAVLINK_SOURCE_COMPONENT` — our component ID (default: `190` MAV_COMP_ID_ONBOARD_COMPUTER)
- `MAVLINK_TARGET_SYSTEM` — FC system ID (default: `1`)
- `MAVLINK_TARGET_COMPONENT` — FC component ID (default: `1`)

**State structure** (`TelemetryState`):
```python
@dataclass
class TelemetryState:
    timestamp: float          # time.time() of last update
    link_ok: bool             # True if received message < 2s ago
    # Position
    lat: float = 0.0          # degrees * 1e7 (MAVLink format)
    lon: float = 0.0
    alt: float = 0.0          # mm (MAVLink format)
    relative_alt: float = 0.0 # mm
    # Attitude (radians)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    # Velocity (cm/s)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    # Battery
    voltage_v: float = 0.0
    current_a: float = 0.0
    remaining_pct: float = 0.0
    # RC channels (normalized -1..1)
    rc_channels: list[float] = field(default_factory=lambda: [0.0]*16)
    # Message counts for diagnostics
    msg_counts: dict[str, int] = field(default_factory=dict)
```

## Affected Files

| File | Operation | Description |
|------|-----------|-------------|
| `src/dfb/mavlink_ingest.py` | create | MAVLink connection, parser loop, TelemetryState, reconnection logic |
| `src/dfb/service.py` | modify | Add lifespan task, `/telemetry` endpoint, import mavlink_ingest |
| `src/dfb/__init__.py` | modify | Export TelemetryState, start_mavlink_task, stop_mavlink_task |
| `pyproject.toml` | modify | Add `pyserial` to dependencies |
| `deploy/flybrain.service` | modify | Add MAVLINK_* env vars (with defaults) |
| `scripts/deploy_deck.sh` | modify | Ensure dialout group membership note |
| `tests/test_mavlink.py` | create | Unit tests for parser, integration test with mavproxy SITL |
| `tests/conftest.py` | modify | Add fixture for mock MAVLink connection |

## Specification

### New Module: `src/dfb/mavlink_ingest.py`

**Public API**:
```python
from dataclasses import dataclass, field
from typing import Optional
import asyncio

@dataclass
class TelemetryState:
    # ... fields as above

async def start_mavlink_task(device: str, baud: int, source_system: int, ...):
    """Start background MAVLink ingestion task. Returns task handle."""

async def stop_mavlink_task(task: asyncio.Task):
    """Stop the background task gracefully."""

def get_telemetry_state() -> TelemetryState:
    """Thread-safe getter for current telemetry state."""
```

**Internal**:
- `MavlinkReader` class encapsulating connection + reader loop
- `_parse_message(msg)` — handles each message type, updates state under lock
- `_reconnect_loop()` — exponential backoff (1s, 2s, 4s, 8s, max 30s)

### Modified: `src/dfb/service.py`

**Lifespan additions**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    get_cpu_engine()
    mavlink_task = await start_mavlink_task(
        device=os.getenv("MAVLINK_DEVICE", "/dev/ttyACM0"),
        baud=int(os.getenv("MAVLINK_BAUD", "57600")),
        source_system=int(os.getenv("MAVLINK_SOURCE_SYSTEM", "255")),
        source_component=int(os.getenv("MAVLINK_SOURCE_COMPONENT", "190")),
        target_system=int(os.getenv("MAVLINK_TARGET_SYSTEM", "1")),
        target_component=int(os.getenv("MAVLINK_TARGET_COMPONENT", "1")),
    )
    yield
    await stop_mavlink_task(mavlink_task)
    shutdown_cpu_engine()
```

**New endpoint**:
```python
@app.get("/telemetry")
async def telemetry():
    state = get_telemetry_state()
    return {
        "timestamp": state.timestamp,
        "link_ok": state.link_ok,
        "position": {"lat": state.lat, "lon": state.lon, "alt": state.alt, "relative_alt": state.relative_alt},
        "attitude": {"roll": state.roll, "pitch": state.pitch, "yaw": state.yaw},
        "velocity": {"vx": state.vx, "vy": state.vy, "vz": state.vz},
        "battery": {"voltage_v": state.voltage_v, "current_a": state.current_a, "remaining_pct": state.remaining_pct},
        "rc_channels": state.rc_channels,
        "message_counts": state.msg_counts,
    }
```

### Modified: `deploy/flybrain.service`

Add Environment lines for MAVLINK_* vars (with defaults matching code).

## Testing Strategy

**Unit tests** (`tests/test_mavlink.py`):
- `test_telemetry_state_defaults` — all fields zero/false initially
- `test_parse_heartbeat` — updates link_ok timestamp
- `test_parse_attitude` — roll/pitch/yaw in radians
- `test_parse_global_position_int` — lat/lon/alt conversion
- `test_parse_sys_status` — voltage/current extraction
- `test_parse_battery_status` — remaining_pct
- `test_parse_rc_channels` — normalization to -1..1
- `test_thread_safety` — concurrent reads/writes don't corrupt state
- `test_reconnect_backoff` — exponential backoff timing

**Integration test** (marked `@pytest.mark.slow`, requires mavproxy):
- `test_mavlink_sitl` — start mavproxy SITL, connect service, verify telemetry updates

**Existing tests**: Ensure no regression in `/health`, `/decide`, `/command`, safety gate.

## Verification Criteria

- [ ] `make check` passes (all tests, lint, coverage ≥80%)
- [ ] `/telemetry` endpoint returns valid JSON with all fields
- [ ] MAVLink connection established on Deck (serial or UDP)
- [ ] Telemetry updates at expected rate (>5Hz for attitude)
- [ ] Link loss detected within 2s (link_ok=false)
- [ ] Auto-reconnect works after cable pull / FC reboot
- [ ] Service survives MAVLink parser exceptions (no crash)
- [ ] Deploy script works with new env vars
- [ ] `dfb telemetry` CLI command works (extend client)

## Estimation

- Complexity: **medium** (2–8h)
- Risk: **medium** (serial config, thread safety, FC integration unknowns)
- Blocking dependencies: **no** (pymavlink already in deps, pyserial is standard)

## Next Step

Run `/aes-build` to implement.