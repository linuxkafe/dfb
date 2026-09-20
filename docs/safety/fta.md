# Fault Tree Analysis (FTA)

## Overview
Top-down analysis for critical hazards per ARP4761. Minimal cut sets identified for each top event.

## Top Events

### TE1: Unintended Command Sent to Flight Controller
```
TE1: Unintended command sent to FC
├── Token gate bypassed
│   ├── G1: Token prediction/brute force (8-char UUID, 30s TTL)
│   │   └── Probability: ~1/(16^8) × requests in 30s window ≈ 10⁻⁹
│   ├── G2: Token replay attack
│   │   └── Mitigated: Single-use, server-side tracking, 30s TTL
│   ├── G3: Token leakage (log exposure)
│   │   └── Mitigation: Tokens not logged, HTTPS/gRPC encryption
│   └── G4: Token reuse (server bug)
│       └── Mitigation: Single-use enforcement, 30s TTL cleanup
├── FC accepts command without verification
│   └── FC bug (outside DFB scope, FC vendor responsibility)
└── MAVLink injection vulnerability
    ├── G5: Serial port compromise (physical access)
    │   └── Probability: Low (requires physical access)
    └── G6: MAVLink protocol exploit (buffer overflow)
        └── Mitigation: pymavlink validated, FC authority
```

**Minimal Cut Sets for TE1:**
| Cut Set | Elements | Probability |
|---------|----------|-------------|
| CS1 | {G1, G3} | ~10⁻⁹ |
| CS2 | {G2, G3} | ~0 (single-use) |
| CS3 | {G5, G6} | Low (physical) |

### TE2: Loss of Telemetry Link Undetected
```
TE2: Loss of telemetry link undetected >5s
├── MAVLink link loss undetected
│   ├── G7: Watchdog task crash/hang
│   │   └── Mitigation: Task monitor, auto-restart
│   ├── G8: MAVLink task stuck in recv_match
│   │   └── Mitigation: 1s timeout on recv_match
│   └── G9: MAVLink task exception not caught
│       └── Mitigation: Exception handler, task restart
├── CRSF link loss undetected
│   ├── G10: Watchdog task crash/hang
│   │   └── Mitigation: Task monitor, auto-restart
│   ├── G11: CRSF parser stuck
│   │   └── Mitigation: Frame timeout, parser reset
│   └── G12: CRSF serial port error
│       └── Mitigation: Serial exception handler, reconnect
├── Both links lost, neither detected
│   └── G13: Common cause (Steam Deck freeze)
│       └── Mitigation: FC independent failsafe (RTL/LAND)
```

**Minimal Cut Sets for TE2:**
| Cut Set | Elements | Probability |
|---------|----------|-------------|
| CS1 | {G7, G10} | Low (independent tasks) |
| CS2 | {G13} | Medium (HW common cause) |

### TE3: Wrong Advisory Accepted by Pilot/FC
```
TE3: Wrong advisory accepted by pilot/FC
├── Safety envelope bypassed
│   ├── G14: Geofence check bypassed
│   │   └── Mitigation: Bounds check on every advisory
│   ├── G15: Altitude floor/ceiling bypassed
│   │   └── Mitigation: AGL check on every advisory
│   ├── G20: Battery reserve check bypassed
│   │   └── Mitigation: Battery check on every advisory
│   ├── G21: Link quality check bypassed
│   │   └── Mitigation: Link age check on every advisory
│   ├── G22: GPS quality check bypassed
│   │   └── Mitigation: GPS fix type ≥3 required
│   ├── G23: Speed/attitude envelope bypassed
│   │   └── Mitigation: Envelope check on every advisory
│   └── G24: FC accepts advisory without validation
│       └── FC responsibility (outside DFB scope)
├── Pilot accepts wrong advisory
│   ├── G25: Advisory appears correct but wrong
│   │   └── Mitigation: Safety envelope, pilot training
│   ├── G26: Advisory mode confusion (MANUAL vs AUTO)
│   │   └── Mitigation: Mode awareness, advisory-only in MANUAL
│   └── G26: Pilot fatigue/complacency
│       └── Mitigation: Pilot currency, simulator training
├── FC accepts wrong advisory
│   └── FC bug (outside DFB scope, FC vendor responsibility)
```

**Minimal Cut Sets for TE3:**
| Cut Set | Elements | Probability |
|---------|----------|-------------|
| CS1 | {G14} | Low (bounds check) |
| CS2 | {G15} | Low (altitude check) |
| CS3 | {G20} | Low (battery check) |
| CS4 | {G21} | Low (link check) |
| CS5 | {G25} | Low (pilot training) |

### TE4: Safety Envelope Bypassed
```
TE4: Safety envelope bypassed (advisory generated despite violation)
├── CRITICAL violation not detected
│   ├── G27: Geofence check returns false positive
│   │   └── Unit test: test_geofence_violation_lat/lon
│   ├── G28: Altitude floor check returns false positive
│   │   └── Unit test: test_altitude_floor
│   ├── G29: Altitude ceiling check returns false positive
│   │   └── Unit test: test_altitude_ceiling
│   ├── G30: Battery reserve check returns false positive
│   │   └── Unit test: test_battery_reserve
│   ├── G31: Link loss check returns false positive
│   │   └── Unit test: test_link_loss
│   └── G32: GPS quality check returns false positive
│       └── Unit test: test_gps_fix_type
├── WARNING violation treated as OK
│   ├── G33: Speed limit check returns false positive
│   │   └── Unit test: test_speed_limit
│   ├── G34: Climb/sink rate check returns false positive
│   │   └── Unit test: test_climb_rate, test_sink_rate
│   ├── G35: Attitude limit check returns false positive
│   │   └── Unit test: test_attitude_limits
│   └── G36: GPS DOP check returns false positive
│       └── Unit test: test_gps_fix_type
├── Envelope logic error
│   ├── G37: CRITICAL violation not escalated to RTL
│   │   └── Code review: advisor.py mode logic
│   ├── G38: WARNING violation not logged
│   │   └── Code review: safety_envelope.py logging
│   └── G39: Envelope constants mismatch (code vs config)
│       └── Single source: DEFAULT_SAFETY_CONFIG
```

**Minimal Cut Sets for TE4:**
| Cut Set | Elements | Probability |
|---------|----------|-------------|
| CS1 | {G27} | Very Low (unit test) |
| CS2 | {G28} | Very Low (unit test) |
| CS3 | {G29} | Very Low (unit test) |
| CS4 | {G30} | Very Low (unit test) |
| CS5 | {G31} | Very Low (unit test) |
| CS6 | {G32} | Very Low (unit test) |
| CS7 | {G33} | Very Low (unit test) |
| CS8 | {G34} | Very Low (unit test) |
| CS8 | {G35} | Very Low (unit test) |
| CS9 | {G36} | Very Low (unit test) |
| CS10 | {G37} | Very Low (code review) |
| CS11 | {G38} | Very Low (code review) |
| CS12 | {G38} | Very Low (single source) |

## Common Cause Failures

| CCF | Description | Mitigation |
|-----|-------------|------------|
| CCF-01 | Steam Deck hardware freeze | FC independent failsafe (RTL/LAND), pilot manual |
| CCF-02 | Steam Deck thermal throttling | CPUQuota=200%, thermal monitoring (planned) |
| CCF-03 | Steam Deck OOM kill | MemoryMax=2G, graceful degradation |
| CCF-03 | Common power loss (battery) | Medium | FC independent battery, pilot manual |
| CCF-04 | RF interference (both links) | Medium | FC failsafe, different frequencies |

## Quantitative Summary

| Top Event | Severity | Min Cut Sets | Residual Risk |
|-----------|----------|--------------|---------------|
| TE1: Unintended command | Catastrophic | 3 | Very Low |
| TE2: Link loss undetected | Hazardous | 2 | Low |
| TE3: Wrong advisory accepted | Hazardous | 5 | Low |
| TE4: Envelope bypassed | Hazardous | 12 | Very Low |

## FTA Completeness Check

- [x] All FHA Catastrophic/Hazardous hazards have FTA
- [x] Minimal cut sets identified for all top events
- [x] Common cause failures identified
- [x] Mitigations traceable to code/tests
- [x] Probability estimates documented (qualitative)
- [x] CCF analysis included

---
*Document version: 0.1.0 | Based on ARP4761 for experimental UAS*