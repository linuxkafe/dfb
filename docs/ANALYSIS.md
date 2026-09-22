# Exhaustive Analysis: Deck Fly Brain (DFB)

**Generated:** 2026-09-22  
**AES Tier:** AES-standard (peer review)  
**Analyst:** opencode / AES

---

## Executive Summary

**DFB is a well-structured, safety-conscious companion compute service** running on Steam Deck (x86_64 Linux, AMD APU) that provides autonomous flight decision-making for FPV drones via MAVLink/CRSF integration with the flight controller.

**But it is NOT production-ready** due to:
1. **Failed quality gate** — test coverage 36% (target 80%)
2. **Broken test** — protobuf version mismatch blocks watchdog test
3. **Dead code** — Vulkan engine (946 lines, 0% coverage, import-time failure)
4. **No CI/CD pipeline** — manual deploy only

---

## 1. What This Project IS

### Architecture

```
Client (dev machine)          Server (Steam Deck)
├── SSH / SSH tunnel          ├── systemd service (flybrain)
├── dfb CLI (Typer)           ├── REST API :8082 (FastAPI)
└── gRPC client               ├── gRPC API :8083
                              ├── MAVLink ingest (/dev/ttyACM0)
                              ├── CRSF/ELRS ingest (/dev/ttyACM1)
                              ├── State Estimator (NED→ENU + GPS/IMU fusion)
                              ├── Safety Envelope (geofence, altitude, battery, link, GPS, speed, attitude)
                              ├── Advisor (waypoint nav, loiter, RTL on violation)
                              ├── Prometheus metrics / health
                              └── Structured JSON logging + correlation IDs
```

### Requirements Coverage (REQUIREMENTS.md — all 20 REQs marked ✅)

| REQ | Capability | Implementation |
|-----|------------|----------------|
| 01 | SSH connectivity (key-only) | `deploy_deck.sh` + systemd |
| 02 | systemd service (auto-start, restart) | `deploy/flybrain.service` |
| 03 | REST + gRPC APIs | `service.py` + `grpc_server.py` |
| 04 | MAVLink + CRSF link | `mavlink_ingest.py` + `crsf_ingest.py` |
| 05 | Client CLI | `cli.py` + `client.py` |
| 06 | Telemetry ingestion | Background tasks with auto-reconnect |
| 07 | Decision engine | `advisor.py` + `state_estimator.py` |
| 08 | Safety gate (token, 30s TTL) | `/confirm/issue`, `/command` + header |
| 09 | State estimator | NED→ENU, equirectangular projection, anomaly flags |
| 10 | Mode awareness | `ADVISORY_COMPATIBLE_MODES` / `MANUAL_MODES` |
| 11 | Safety-constrained advisory | `check_safety()` → RTL on CRITICAL |
| 12 | Safety envelope | 7 categories, CRITICAL + WARNING severity |
| 13 | CRSF CRC8 + framing | `crsf_ingest.py` incremental parser |
| 14 | gRPC unary + streaming | `GetTelemetryStream` with interval |
| 15 | REST endpoints | All 7 endpoints implemented |
| 16 | Prometheus + health | `metrics.py` + `/health` component breakdown |
| 17 | SSH keys only | Enforced by deploy script |
| 18 | JSON logging + correlation IDs | `logging.py` middleware |
| 19 | FC firmware untouched | MAVLink/CRSF integration only |
| 20 | Auto-restart + degradation | systemd `Restart=on-failure` + watchdog |

### Non-Functional Baseline

- Advisory latency target: **< 100ms** (CPU EP measured 6.2× faster than raw PyTorch)
- Deployment: systemd, `MemoryMax=2G`, `CPUQuota=200%`
- Transport: SSH tunnel (control), UDP/TCP (MAVLink), serial (CRSF)
- Dependencies: pymavlink, numpy — **no PyTorch runtime dependency**

---

## 2. What This Project PRETENDS TO BE (Gaps)

| Claim | Reality | Severity |
|-------|---------|----------|
| "Fly Brain semantics are partially [UNKNOWN]" (VISION.md) | Core advisory logic exists (waypoint nav, loiter, RTL on violation) but **no higher-level autonomy** (obstacle avoidance, mission planning, computer vision). "Fly Brain" is really a **safety-constrained advisory service**. | HIGH |
| All REQs ✅ | **Coverage 36%** (target 80%). CLI (0%), gRPC service (6-14%), vulkan_engine (0%), main service (6%) largely untested. | HIGH |
| Safety traceability complete | 5/46 hazards have **no automated test** (FC-38, FC-41, FC-43, FC-44, FC-46) — justified as N/A but not exercised. FC-40 watchdog test **fails** (protobuf version mismatch). | MEDIUM |
| "CPU EP sufficient for current advisory load" | **Vulkan engine is dead code** (0% coverage, requires SPIR-V shaders, protobuf version mismatch breaks import). CPU fallback (numpy MLP) is what actually runs. | MEDIUM |
| "Remote development workflow: code here, compute there" | `deploy_deck.sh` works but **no CI/CD pipeline** — manual deploy only. No staging/prod separation. | MEDIUM |

### Coverage Breakdown (pytest-cov)

```
Name                                Stmts   Miss  Cover
-------------------------------------------------------
src/__init__.py                         1      0   100%
src/dfb/__init__.py                     7      0   100%
src/dfb/advisor.py                     76      7    91%
src/dfb/cli.py                         65     65     0%
src/dfb/client.py                     272    115    58%
src/dfb/cpu_engine.py                  38     22    42%
src/dfb/crsf_ingest.py                189     86    54%
src/dfb/grpc/__init__.py                0      0   100%
src/dfb/grpc/flybrain_pb2.py           81     75     7%
src/dfb/grpc/flybrain_pb2_grpc.py      86     86     0%
src/dfb/grpc_server.py                 43     37    14%
src/dfb/grpc_service.py               115    101    12%
src/dfb/health.py                      54      8    85%
src/dfb/logging.py                     54      6    89%
src/dfb/mavlink_ingest.py             185     63    66%
src/dfb/metrics.py                     47      8    83%
src/dfb/safety_envelope.py            102      5    95%
src/dfb/service.py                    253    238     6%
src/dfb/state_estimator.py            100     22    78%
src/dfb/vulkan_engine.py              532    532     0%
src/main.py                             4      1    75%
-------------------------------------------------------
TOTAL                                2304   1477    36%
```

**Critical uncovered modules:**
- `service.py` — 238/253 lines (watchdog, endpoints, token flow)
- `grpc_service.py` / `grpc_server.py` — 101-115/115-116 lines
- `vulkan_engine.py` — 532/532 lines (dead code)
- `cli.py` — 65/65 lines (0%)

---

## 3. What This Project COULD BE (Creative Extensions)

Given the existing architecture, these are **architecturally natural** next steps:

### 1. Obstacle-Aware Advisory (High Value)
- Fuse CRSF/ELRS **GPS + optical flow** or add **depth camera** (Deck has USB-C)
- Extend `SafetyConfig` with `obstacle_distance_min`, `min_clearance`
- Advisory computes **collision-free heading** (potential fields / RRT*)

### 2. Mission Planning Layer (Natural Progression)
- Current: single waypoint → heading/alt/speed
- Add: **waypoint sequences**, mission state machine (TAKEOFF → WAYPOINT_N → LOITER → RTL)
- Persist missions to disk; API: `/mission/upload`, `/mission/start`, `/mission/status`

### 3. Simulated Hardware-in-the-Loop (HITL) CI
- `sim/` already has MuJoCo + ONNX export
- Add **GitHub Action** that spins up SITL (ArduPilot/PX4) + DFB service + runs maze benchmark
- Gate: `make test-deck` in CI (currently manual only)

### 4. Multi-Drone Fleet Coordination
- Service already stateless per-request → add **fleet manager** (separate process)
- gRPC stream `/TelemetryStream` already supports multi-drone (add `vehicle_id` field)
- Swarm behaviors: formation, collision avoidance, relay

### 5. On-Deck ML Inference (Vulkan EP Revival)
- Fix protobuf version → regenerate `flybrain_pb2.py` with current `protoc`
- Compile shaders (`glslc`) → enable Vulkan EP
- Export trained policy (ONNX) → run on Deck GPU for **learned advisory**

### 6. Regulatory Compliance Mode
- Configurable `SafetyConfig` per country (EU: 120m ceiling, US: 400ft, etc.)
- GeoJSON geofence loading from file
- Audit log export for authorities

### 7. Web UI / Cockpit (Non-Goal but Doable)
- React + Mapbox/Leaflet showing real-time telemetry, advisory, safety status
- WebSocket `/ws/telemetry` for live updates
- Touch-friendly for Deck screen

---

## 4. AES Peer Review — Findings

### 🔴 BLOCKER: Test Coverage (36% vs 80% target)
**Location:** `Makefile:44` → `make test-check` fails  
**Impact:** Quality gate blocks `make check` and by extension any CI/CD  
**Fix:** Add tests for:
- `service.py` (watchdog, endpoints, token flow) — 238/253 lines uncovered
- `grpc_service.py` / `grpc_server.py` — 101-115/115-116 lines uncovered
- `vulkan_engine.py` — either test or **remove** (dead code)
- `cli.py` — 0% coverage, testable via `typer.testing.CliRunner`

### 🔴 BLOCKER: Protobuf Version Mismatch Breaks Watchdog Test
**Error:** `gencode 7.35.1 runtime 6.33.6` — generated code incompatible with runtime  
**Root Cause:** `proto/flybrain.proto` compiled with newer `protoc` than installed `protobuf` runtime  
**Fix:** 
```bash
pip install 'protobuf>=7.35.1'  # or regenerate with current protoc
# Regenerate:
protoc --proto_path=proto --python_out=src/dfb/grpc --grpc_python_out=src/dfb/grpc proto/flybrain.proto
```

### 🟡 MAJOR: Vulkan Engine is Dead Code
**File:** `src/dfb/vulkan_engine.py` (946 lines, 0% coverage)  
**Issue:** Requires SPIR-V shaders (`shaders/*.comp`), `libvulkan.so`, `glslc` — none verified on Deck. Protobuf mismatch prevents import.  
**Options:**
- **Delete** — CPU engine (numpy) meets latency target (<100ms)
- **Fix + Test** — add `sim/test_vulkan.py`, CI with `MESA_LOADER_DRIVER_OVERRIDE=zink`
- **Archive** — move to `experimental/` with README

### 🟡 MAJOR: Safety Traceability Has Gaps
**5 hazards lack automated tests** (justified in `N_A_TESTS`):
- FC-38: Unintended RTL — "no exec harness"
- FC-41: CRSF task dead — "test planned"
- FC-43: OOM kill — "systemd config"
- FC-44: CPU saturation — "systemd config"
- FC-46: gRPC backpressure — "interval min 20ms"

**Recommendation:** Add **integration-style tests** that exercise the watchdog paths (FC-40, FC-41) and resource limits (FC-43, FC-44) using mocked systemd or container limits.

### 🟡 MAJOR: No CI/CD Pipeline
**Missing:** `.github/workflows/ci.yml` (referenced in CLAUDE.md:41 but absent)  
**Evidence:** `.gitlab-ci.yml` and `.woodpecker.yml` exist but minimal (likely not run)  
**Risk:** No automated validation on PR → drift between local `make check` and reality

### 🟡 MEDIUM: CLI Tests 0% Coverage
**File:** `src/dfb/cli.py` — all commands untested  
**Fix:** Use `typer.testing.CliRunner` to test each subcommand

### 🟡 MEDIUM: gRPC Service Largely Untested
**Coverage:** 6-14% across `grpc_service.py`, `grpc_server.py`, `flybrain_pb2.py`  
**Critical paths untested:** `GetTelemetryStream`, `Decide`, token issue/verify, `SendCommand`

### 🟢 MINOR: Design System Docs Incomplete
**File:** `docs/DESIGN.md` — minimal (palette, typography, spacing only)  
**Gap:** No component library, no icon mapping, no dark/light mode tokens per AES FR-D5

### 🟢 MINOR: ROADMAP.md Trivial
**Content:** 3 generic items (Initial Setup, First Feature, Polish) — no actual milestones  
**Should reflect:** Vulkan decision, HITL CI, Mission Planning, Fleet, Regulatory modes

---

## 5. Diffstory — Required Changes

| File | Change | Why | Risk |
|------|--------|-----|------|
| `Makefile` | Fix protobuf version or regenerate gRPC code | Unblocks watchdog test | Low |
| `tests/test_health.py` | Fix import / mock `grpc` imports in watchdog test | Unblocks test | Low |
| `src/dfb/vulkan_engine.py` | **Delete** or **archive** (dead code) | Reduces complexity, removes import-time failure | Low if deleted; Medium if fixed |
| `tests/` | Add 30+ tests for service, gRPC, CLI | Achieve 80% coverage | Medium (effort) |
| `.github/workflows/ci.yml` | Create CI pipeline (lint, test, safety-check, coverage) | Automates quality gates | Low |
| `docs/ROADMAP.md` | Replace with real milestones | Project direction visible | None |
| `docs/DESIGN.md` | Expand per AES FR-D5 | Frontend readiness | None |

---

## 6. Remaining Risks / Watch Items

1. **Steam Deck Hardware Specificity**: Thermal throttling, vibration limits, battery drain — no integration tests on actual Deck hardware (only `test-deck` manual target)
2. **FC Firmware Variability**: ArduPilot vs PX4 mode mappings in `state_estimator.py` and `mavlink_ingest.py` are **hardcoded** — may break with firmware updates
3. **Single-Threaded MAVLink Reader**: Uses `asyncio.to_thread` for blocking `pymavlink` — under high message rates, may queue latency
4. **Token Store In-Memory**: `_confirmation_tokens` dict lost on restart — tokens invalidated across service restart (acceptable per REQ-08 30s TTL but worth noting)
5. **No Authentication on APIs**: REST/gRPC exposed on `0.0.0.0` — relies on SSH tunnel for security. If tunnel breaks, APIs open on LAN.

---

## 7. Recommended Immediate Priority

1. **Fix protobuf version / regenerate gRPC code** → unblock watchdog test
2. **Decide on Vulkan**: delete or fix+test
3. **Add CI pipeline** (`.github/workflows/ci.yml`)
4. **Incrementally add tests** to reach 80% (focus: `service.py`, `grpc_service.py`, `cli.py`)
5. **Update ROADMAP.md** with real milestones

---

## 8. Validation Performed

| Check | Command | Result |
|-------|---------|--------|
| Tests | `make test` | 1 failed, 98 passed, 7 skipped (protobuf mismatch) |
| Lint | `make lint` | Passed |
| Safety | `make safety-check` | **Passed** — 20 REQs, 46 hazards, 41 with tests, 5 N/A justified |
| Coverage | `make test-check` | **Failed** — 36% < 80% |
| Full check | `make check` | **Failed** — coverage + watchdog test |

---

## 9. Appendix: Safety Traceability Metrics

| Metric | Count | Target |
|--------|-------|--------|
| Requirements (REQ-01..REQ-20) traced | 20/20 | 100% |
| Hazards tracked (FC-01..FC-46 from FHA) | 46/46 | 100% |
| Hazards with automated test evidence | 41/46 | ≥41 |
| Hazards documented as non-automated (N/A) | 5/46 | ≤5 |
| Orphan hazards (no REQ link) | 0/46 | 0 |
| Referenced tests that do not exist | 0 | 0 |

**Source:** `docs/safety/traceability.py` — single source of truth, validated by `make safety-check`