# System Safety Assessment (SSA)

## 1. System Description

### 1.1 System Overview
The Deck Fly Brain (DFB) is an **advisory-only** companion computer system for FPV drones running on Steam Deck hardware (AMD VanGogh APU, 8GB RAM, SteamOS). It provides autonomous flight decision-making capabilities as a ground-station companion compute node.

### 1.2 System Boundaries
- **In scope**: DFB service (FastAPI on Steam Deck), MAVLink/CRSF telemetry ingestion, state estimator, advisory decision engine, safety envelope, token confirmation gate, gRPC/HTTP APIs
- **Out of scope**: Flight controller firmware (ArduPilot/INAV/PX4), radio hardware, pilot interface, airframe

### 1.3 Functions
| Function | Description | Criticality |
|----------|-------------|-------------|
| Telemetry Ingestion | MAVLink/CRSF parsing, validation, state estimation | High |
| State Estimation | NED→ENU transform, GPS/IMU fusion, anomaly detection | High |
| Advisory Generation | Waypoint navigation, safety envelope checking, mode awareness | High |
| Safety Envelope | Geofence, altitude, battery, link, GPS, speed, attitude limits | Critical |
| Token Confirmation | Single-use tokens for safety-critical commands | Critical |
| Command Proxy | Forward validated commands to FC via MAVLink | High |
| Health Monitoring | Component status, link quality, resource usage | Medium |
| gRPC/HTTP API | Telemetry streaming, advisory queries, command interface | Medium |

### 1.4 Interfaces
| Interface | Protocol | Direction | Safety Impact |
|-----------|----------|-----------|---------------|
| MAVLink Serial | MAVLink v2 / 57600 baud | FC → DFB | High (telemetry) |
| CRSF Serial | CRSF / 420000 baud | RX → DFB | High (telemetry) |
| HTTP/REST | JSON / 8082 | Client ↔ DFB | Medium (advisory) |
| gRPC | Protobuf / 8083 | Client ↔ DFB | Medium (advisory) |
| MAVLink Commands | MAVLink v2 | DFB → FC | Critical (commands) |

### 1.5 Operating Environment
- **Platform**: Steam Deck (AMD VanGogh, 4C/8T Zen2, 8GB RAM, SteamOS)
- **Network**: LAN/WiFi between client and Steam Deck
- **RF Link**: MAVLink telemetry radio / ELRS Crossfire
- **Flight Phases**: Pre-flight, takeoff, cruise, loiter, RTL, landing, emergency
- **Weather**: VFR only, wind <15 m/s (advisory)

## 2. Safety Requirements

### 2.1 Derived from Hazards (see FHA)
| SR-ID | Requirement | Hazard | Verification |
|-------|-------------|--------|--------------|
| SR-01 | Advisory shall not recommend heading/altitude/speed outside safety envelope | H1 | test_advisor.py |
| SR-02 | Advisory shall not be generated in MANUAL/ACRO modes | H2 | test_advisor.py |
| SR-03 | No command sent to FC without valid confirmation token | H3 | test_client.py |
| SR-04 | MAVLink link loss detected within 2s | H4 | test_health.py |
| SR-05 | CRSF link loss detected within 5s | H4 | test_health.py |
| SR-06 | Advisory generation latency < 100ms | H1, H2 | benchmark |
| SR-07 | Service shall auto-restart on failure | H2, H4 | test_health.py |
| SR-08 | Resource usage shall not exceed MemoryMax=2G, CPUQuota=200% | - | deploy test |
| SR-09 | Token shall be single-use with 30s TTL | H3 | test_client.py |
| SR-10 | FC firmware never modified by DFB | All | Code review |

## 3. Safety Architecture

### 3.1 Defense in Depth Layers
```
Layer 1: FC Authority (Ultimate)
    Flight controller retains ultimate control authority
    DFB is advisory-only; FC executes or rejects commands

Layer 2: Safety Envelope (Advisory Constraint)
    Geofence, altitude floor/ceiling, battery reserve, link quality
    GPS quality, speed/attitude limits
    CRITICAL violations → advisory mode = RTL
    WARNING violations → advisory continues with warning

Layer 3: Mode Awareness (Advisory Gating)
    MANUAL/ACRO/STABILIZE → advisory-only mode (no mode change)
    GUIDED/AUTO/LOITER → full advisory with mode recommendation
    RTL/LAND/SMART_RTL → no interference (FC safety mode)

Layer 4: Token Confirmation Gate (Command Authorization)
    Single-use tokens, 30s TTL, X-Confirmation-Token header
    Prevents unauthorized/replay commands

Layer 5: Token Confirmation + Human-in-Loop (Command Execution)
    Pilot must explicitly confirm safety-critical commands
    FC remains ultimate authority to accept/reject
```

### 3.2 Data Flow Safety
```
MAVLink/CRSF → Telemetry Ingestion → State Estimator → Advisor → Safety Envelope → Advisory
                                                              ↓
                                          Token Gate → Command Proxy → FC
```

## 4. Safety Requirements Allocation

| Component | Safety Functions | SIL/DAL Equivalent |
|-----------|------------------|-------------------|
| FC Firmware | Flight stabilization, command execution, failsafe | DAL A (by vendor) |
| DFB Safety Envelope | Advisory constraint checking | DAL C equivalent |
| DFB Token Gate | Command authorization | DAL C equivalent |
| DFB Watchdog | Link monitoring, auto-restart | DAL D equivalent |
| DFB Advisor | Advisory generation | DAL D equivalent |

## 5. Verification Strategy

| Method | Scope | Evidence |
|--------|-------|----------|
| Unit Test | Safety envelope, advisor logic, token gate | test_advisor.py, test_client.py, test_health.py |
| Integration Test | MAVLink/CRSF ingestion, health endpoints | test_mavlink.py, test_crsf.py, test_health.py |
| Chaos Test | Link loss, OOM, CPU stress | test_health.py (planned) |
| Peer Review | Safety artifacts (SSA, FHA, FTA, Safety Case) | PR reviews |
| Traceability | Requirements → Hazards → Tests | make safety-check |

## 6. Residual Risk Assessment

| Hazard | Residual Risk | Justification |
|--------|---------------|---------------|
| Wrong advisory accepted by pilot | Low | Pilot trained, FC authority, safety envelope |
| Undetected link loss >5s | Low | Watchdog 5s timeout, FC failsafe |
| Wrong advisory in MANUAL mode | Low | Advisory-only mode, pilot in control |
| Token replay/reuse | Very Low | Single-use, 30s TTL, HTTPS/gRPC |
| Safety envelope bypass | Very Low | All advisories checked, FC authority |
| Common cause failure (Steam Deck HW) | Medium | FC independent, pilot manual override |

## 6.1 Safety Case Summary (GSN)

```
Goal: Residual risk acceptable for experimental flight
  Strategy: Defense in depth
    Sub-goal 1: FC remains authority
      Evidence: REQ-19, architecture diagram
    Sub-goal 2: Advisory constrained by safety envelope
      Evidence: FHA mitigations, test_advisor.py
    Sub-goal 3: Commands require explicit confirmation
      Evidence: Token gate, test_client.py
    Sub-goal 4: Link loss detected and handled
      Evidence: Watchdog, test_health.py
    Sub-goal 5: System fails safe
      Evidence: Graceful degradation, no command on link loss
```

## 7. Operational Constraints

- **Experimental use only** - not for commercial passenger carrying
- **Pilot in loop** - manual override always possible
- **VFR only** - visual flight rules, visual line of sight
- **Weather** - wind <15 m/s, visibility >3km
- **Geofence** - configurable, default unrestricted
- **Altitude** - 5-120m AGL configurable
- **Battery reserve** - 20% minimum
- **Link budget** - RF margin >10dB (ELRS)

## 8. Maintenance & Updates

- Safety artifacts in `docs/safety/` version-controlled with code
- `make safety-check` CI gate validates traceability
- Peer review required for safety artifact changes
- Artifacts updated with each release affecting safety functions

---
*Document version: 0.1.0 | Based on ARP4761/ISO 26262 lite for experimental UAS*