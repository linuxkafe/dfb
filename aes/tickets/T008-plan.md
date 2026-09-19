---
ticket: T008
phase: plan
status: done
created: 2026-09-19
tier: standard
requires:
  - aes/kanban.md
  - aes/tickets/T008-decision-engine-telemetry.md
produces:
  - aes/tickets/T008-plan.md
blocked_by: T007
---

# T008 — Plan: Decision Engine with Real Telemetry

## Reconnaissance Summary

**Existing decision engine** (`src/dfb/cpu_engine.py`):
- Simple MLP with 100→64→4 architecture (numpy)
- Takes flattened 10x10 grid as input, outputs 4 actions (UP/DOWN/LEFT/RIGHT)
- Used by `/decide` endpoint in `service.py`
- Random weights (seed=42), no training

**Existing telemetry** (`src/dfb/mavlink_ingest.py`):
- `TelemetryState` dataclass with position, attitude, velocity, battery, RC channels
- Thread-safe, updated at ~10-50Hz from MAVLink
- `/telemetry` endpoint exposes current state

**Current `/decide` endpoint** (`service.py`):
- Expects maze grid input (position, grid, exit)
- Returns discrete action + confidence
- No integration with real telemetry

**Client/CLI** (`client.py`, `cli.py`):
- `DeckClient.decide()` takes maze grid
- CLI `dfb decide` takes JSON maze state
- No telemetry-aware decision command

## Hostile Analysis

### ASSUMPTIONS I AM MAKING

- [KNOWN] T007 provides `get_telemetry_state()` with position, attitude, velocity, battery, link_ok
- [KNOWN] CPU engine is a simple MLP - can be extended or replaced
- [INFERRED] "State estimation" means fusing noisy sensor data into consistent state (complementary filter or EKF)
- [INFERRED] "Advisory decisions" means continuous outputs (heading, altitude, speed) not discrete maze moves
- [ASSUMED] Flight controller remains authority - we only advise, never command directly
- [ASSUMED] Safety envelope checks: geofence (lat/lon bounds), altitude floor/ceiling, battery reserve %, link_ok
- [ASSUMED] FC mode from HEARTBEAT message (need to parse custom_mode/base_mode)
- [UNKNOWN] Whether to keep maze-based MLP or replace with physics-informed policy
- [UNKNOWN] Mission goal format (waypoint, loiter, RTL, follow)

### WHAT WAS NOT SPECIFIED (that matters)

- State estimator choice: complementary filter (simpler) vs EKF (filterpy) vs custom
- Advisory output format: continuous (heading/alt/speed) vs discrete (mode + params)
- How mission goal is provided (API param, config, separate endpoint)
- Whether to fuse GPS + IMU or just use raw MAVLink (already fused by FC)
- Integration with existing MLP: augment input? replace? parallel?

### ALTERNATIVES NOT CHOSEN

| Option | Reason |
|--------|--------|
| Full EKF (filterpy) | Adds dependency; FC already runs EKF; complementary filter sufficient for advisory |
| Replace MLP entirely | Maze MLP is demo; real policy needs different architecture; keep both for now |
| MAVLink command injection | FC is safety authority; advisory only per REQUIREMENTS.md |
| gRPC streaming for decisions | REST polling sufficient for 1-10Hz advisory; defer to T011 |

### RISKS AND SIDE EFFECTS

1. **Mode confusion**: If FC in MANUAL, advisory could conflict with pilot; must check mode
2. **Stale telemetry**: 2s timeout may be too slow for fast dynamics; need freshness check
3. **Safety envelope gaps**: Geofence config not defined; battery reserve threshold not set
4. **API breaking change**: `/decide` signature changes from maze → telemetry-aware
5. **Filter tuning**: Complementary filter gains need tuning for deck IMU characteristics

### COST OF BEING WRONG: MEDIUM

- Wrong advisory could suggest unsafe heading/altitude (mitigated by FC authority)
- API break requires client update (CLI is ours; external clients need migration)
- Filter divergence if gains wrong (bounded by safety envelope)

### SCOPE BOUNDARY

**In**: Complementary filter for attitude/velocity, safety envelope (geofence, altitude, battery, link), mode-aware advisory, new `/decide` API, CLI `dfb decide --telemetry`

**Out**: Low-level control, CRSF (T010), gRPC (T011), learned policy training, MAVLink command injection

### INVITATION FOR CONTRADICTION

What if FC doesn't send HEARTBEAT with custom_mode? — fallback to base_mode. What if GPS denied? — use relative_alt + optical flow (not in scope). What if we need learned policy? — separate ticket.

## Technical Approach

### 1. State Estimation Module (`src/dfb/state_estimator.py`)

**Complementary filter** for attitude (IMU + GPS heading) and velocity (GPS + IMU):
- Attitude: fuse FC-reported attitude (already EKF'd by FC) with GPS course over ground for yaw correction
- Velocity: fuse GPS velocity (NED) with accelerometer (if available) — for now trust FC's GLOBAL_POSITION_INT vx/vy/vz
- Since FC runs its own EKF, our estimator mainly: validates consistency, detects anomalies, provides smoothed derivatives

**Simpler approach**: FC state is already filtered. Our "estimator" = validation + safety checks + coordinate transforms.

```python
@dataclass
class EstimatedState:
    # Position (ENU frame, meters)
    north: float = 0.0
    east: float = 0.0
    down: float = 0.0
    # Velocity (ENU, m/s)
    vn: float = 0.0
    ve: float = 0.0
    vd: float = 0.0
    # Attitude (radians, ENU)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0  # True north referenced
    # Metadata
    timestamp: float = 0.0
    valid: bool = False
    gps_fix_type: int = 0  # 0=none, 1=no fix, 2=2D, 3=3D, 4=DGPS, 5=RTK
```

### 2. Safety Envelope (`src/dfb/safety_envelope.py`)

```python
@dataclass
class SafetyConfig:
    # Geofence (lat/lon bounds, degrees)
    min_lat: float = 0.0
    max_lat: float = 0.0
    min_lon: float = 0.0
    max_lon: float = 0.0
    # Altitude (meters, AGL)
    min_alt: float = 10.0
    max_alt: float = 120.0
    # Battery
    min_battery_pct: float = 20.0
    # Link
    require_link_ok: bool = True
    max_link_age_s: float = 2.0

def check_safety(state: EstimatedState, config: SafetyConfig) -> tuple[bool, list[str]]:
    """Returns (safe, violations)."""
```

### 3. Advisory Decision Engine (`src/dfb/advisor.py`)

```python
@dataclass
class Advisory:
    """Continuous advisory output."""
    heading_deg: float        # 0-360, true north
    altitude_m: float         # Target altitude AGL
    speed_mps: float          # Target ground speed
    mode: str                 # LOITER, GUIDED, RTL, etc.
    reason: str               # Human-readable explanation

class Advisor:
    def __init__(self, safety_config: SafetyConfig):
        self.safety = safety_config

    def advise(self, state: EstimatedState, goal: MissionGoal) -> Advisory:
        # 1. Check safety envelope
        safe, violations = check_safety(state, self.safety)
        if not safe:
            return Advisory(..., mode="RTL", reason=f"Safety: {violations}")

        # 2. Check FC mode compatibility
        if not self._mode_allows_advisory(state.flight_mode):
            return Advisory(..., mode=state.flight_mode, reason="FC mode not compatible")

        # 3. Compute advisory based on goal
        # Simple version: point-to-waypoint
        heading = bearing_to(state, goal.target_lat, goal.target_lon)
        altitude = goal.target_alt
        speed = goal.target_speed
        return Advisory(heading, altitude, speed, "GUIDED", "Navigating to waypoint")
```

### 4. Updated `/decide` Endpoint

New request/response:
```python
class DecideRequest(BaseModel):
    # Mission goal (optional - uses defaults from config)
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    target_alt: Optional[float] = None
    target_speed: Optional[float] = None
    # Or use current telemetry automatically
    use_telemetry: bool = True

class DecideResponse(BaseModel):
    advisory: Advisory  # New continuous output
    safety: SafetyStatus  # Violations, link status, battery
    # Legacy fields for backward compatibility
    action: Optional[str] = None
    confidence: Optional[float] = None
    logits: Optional[List[float]] = None
```

### 5. CLI Extension

Add `dfb decide --telemetry` flag that calls `/decide` with `use_telemetry=true`.

### 6. HEARTBEAT Parsing Enhancement

Update `mavlink_ingest.py` to extract flight mode from HEARTBEAT:
- `base_mode` (MAV_MODE_FLAG)
- `custom_mode` (PX4/ArduPilot specific)
- Map to standard modes: MANUAL, STABILIZE, AUTO, GUIDED, RTL, etc.

## Affected Files

| File | Operation | Description |
|------|-----------|-------------|
| `src/dfb/state_estimator.py` | create | Complementary filter / validation layer |
| `src/dfb/safety_envelope.py` | create | Geofence, altitude, battery, link checks |
| `src/dfb/advisor.py` | create | Advisory decision logic |
| `src/dfb/mavlink_ingest.py` | modify | Parse HEARTBEAT for flight mode |
| `src/dfb/service.py` | modify | New `/decide` endpoint with telemetry integration |
| `src/dfb/__init__.py` | modify | Export new public API |
| `src/dfb/client.py` | modify | Add `decide_telemetry()` method |
| `src/dfb/cli.py` | modify | Add `--telemetry` flag to `decide` command |
| `pyproject.toml` | modify | Add `filterpy` optional dep (for EKF evaluation) |
| `tests/test_advisor.py` | create | Unit tests for advisor, safety, estimator |

## Specification

### New Types

```python
# state_estimator.py
@dataclass
class EstimatedState:
    north: float; east: float; down: float
    vn: float; ve: float; vd: float
    roll: float; pitch: float; yaw: float
    timestamp: float; valid: bool; gps_fix_type: int
    flight_mode: str  # From HEARTBEAT

# safety_envelope.py
@dataclass
class SafetyConfig: ...
@dataclass
class SafetyStatus:
    safe: bool
    violations: list[str]
    battery_pct: float
    link_ok: bool
    link_age_s: float

# advisor.py
@dataclass
class MissionGoal:
    target_lat: float; target_lon: float; target_alt: float; target_speed: float
@dataclass
class Advisory:
    heading_deg: float; altitude_m: float; speed_mps: float
    mode: str; reason: str
```

### Service Endpoint Changes

- `POST /decide` accepts optional mission goal, uses telemetry if `use_telemetry=true`
- Returns `DecideResponse` with `advisory` + `safety` + legacy fields
- Deprecation path: old maze-based request still works but returns advisory

## Testing Strategy

**Unit tests** (`tests/test_advisor.py`):
- `test_complementary_filter` — attitude/velocity fusion correctness
- `test_safety_envelope_geofence` — violations detected outside bounds
- `test_safety_envelope_altitude` — floor/ceiling respected
- `test_safety_envelope_battery` — RTL triggered below reserve
- `test_safety_envelope_link` — link loss triggers RTL
- `test_advisor_mode_compatibility` — only advises in AUTO/GUIDED
- `test_advisor_waypoint_navigation` — heading/alt/speed computed correctly
- `test_advisor_rtl_on_violation` — safety violation forces RTL advisory

**Integration tests**:
- `test_decide_endpoint_telemetry` — `/decide` with `use_telemetry=true` returns advisory
- `test_decide_endpoint_legacy` — maze request still works (backward compat)
- `test_cli_decide_telemetry` — `dfb decide --telemetry` works

## Verification Criteria

- [ ] `make check` passes (all tests, lint, coverage ≥80% for new code)
- [ ] `/decide` with `use_telemetry=true` returns continuous advisory (heading, altitude, speed)
- [ ] Safety envelope rejects unsafe advisories (geofence, altitude, battery, link)
- [ ] FC mode checked — no advisory in MANUAL/STABILIZE
- [ ] HEARTBEAT parsing extracts flight_mode correctly
- [ ] `dfb decide --telemetry` works from CLI
- [ ] Legacy maze `/decide` still works (backward compat)
- [ ] No regressions in T007 telemetry ingestion

## Estimation

- Complexity: **medium** (2–8h)
- Risk: **medium** (safety-critical logic, API changes)
- Blocking dependencies: **no** (T007 complete, numpy in deps)