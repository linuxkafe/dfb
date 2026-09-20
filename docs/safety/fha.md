# Functional Hazard Analysis (FHA)

## Overview
This FHA identifies failure conditions for the Deck Fly Brain (DFB) system and classifies their severity per ARP4761/ISO 26262 lite for experimental UAS.

## Severity Classification
| Level | Definition | Example |
|-------|------------|---------|
| **Catastrophic** | Loss of aircraft, fatality | Unintended arm/disarm, uncontrolled flight into terrain |
| **Hazardous** | Serious injury, major damage | Wrong advisory in auto mode, lost link undetected |
| **Major** | Minor injury, minor damage | Advisory in manual mode, degraded link |
| **Minor** | Nuisance, operational delay | Spurious warning, brief link loss |
| **No Effect** | No safety impact | Cosmetic UI issue |

## Failure Conditions

| FC | Function | Failure Condition | Phase | Severity | Mitigation |
|----|----------|-------------------|-------|----------|------------|
| **FC-01** | Telemetry Ingestion | MAVLink link loss undetected >5s | Flight | **Hazardous** | Watchdog 2s timeout, FC failsafe |
| **FC-02** | Telemetry Ingestion | CRSF link loss undetected >10s | Flight | **Hazardous** | Watchdog 5s timeout, CRSF RSSI monitor |
| **FC-03** | Telemetry Ingestion | Stale position data (>2s) | Flight | **Hazardous** | Timestamp validation, link_age check |
| **FC-04** | Telemetry Ingestion | Stale attitude data (>2s) | Flight | **Hazardous** | Timestamp validation, link_age check |
| **FC-05** | Telemetry Ingestion | MAVLink parse error (corrupt frame) | Flight | **Major** | CRC validation, frame discard |
| **FC-06** | Telemetry Ingestion | CRSF CRC error | Flight | **Major** | CRC8 validation, frame discard |
| **FC-07** | State Estimation | GPS position jump >50m | Flight | **Hazardous** | Equirectangular validation, Δ threshold |
| **FC-08** | State Estimation | Altitude discrepancy >20m | Flight | **Hazardous** | Baro/GPS cross-check |
| **FC-09** | State Estimation | Velocity spike >50 m/s | Flight | **Major** | Velocity sanity check |
| **FC-10** | State Estimation | Attitude angle >90° (inverted) | Flight | **Major** | Attitude sanity check |
| **FC-11** | Advisory Generation | Wrong heading recommendation | Flight | **Hazardous** | Safety envelope, bearing validation |
| **FC-12** | Advisory Generation | Wrong altitude recommendation | Flight | **Hazardous** | Safety envelope (5-120m), FC authority |
| **FC-13** | Advisory Generation | Wrong speed recommendation | Flight | **Hazardous** | Safety envelope (0-25 m/s), FC authority |
| **FC-14** | Advisory Generation | Advisory generated in MANUAL mode | Flight | **Major** | Mode check, advisory-only mode |
| **FC-15** | Advisory Generation | Advisory generated in ACRO mode | Flight | **Major** | Mode check, advisory-only mode |
| **FC-16** | Advisory Generation | Advisory during RTL/LAND (FC safety) | Flight | **Minor** | Mode check, no interference |
| **FC-17** | Advisory Generation | No advisory when needed (lost link) | Flight | **Major** | Watchdog, FC fallback (RTL) |
| **FC-18** | Advisory Generation | No advisory when battery critical | Flight | **Major** | Battery monitor, RTL at 20% |
| **FC-19** | Advisory Generation | No advisory when geofence breach | Flight | **Hazardous** | Geofence check, RTL advisory |
| **FC-20** | Advisory Generation | No advisory when altitude breach | Flight | **Hazardous** | Altitude floor/ceiling check |
| **FC-21** | Advisory Generation | Advisory with stale telemetry | Flight | **Hazardous** | Link age check, link_ok flag |
| **FC-22** | Safety Envelope | Geofence breach not detected | Flight | **Hazardous** | Lat/lon bounds check |
| **FC-23** | Safety Envelope | Altitude floor breach not detected | Flight | **Hazardous** | AGL floor check (5m default) |
| **FC-24** | Safety Envelope | Altitude ceiling breach not detected | Flight | **Hazardous** | AGL ceiling check (120m default) |
| **FC-25** | Safety Envelope | Battery reserve <20% not detected | Flight | **Major** | Battery monitor, RTL at 20% |
| **FC-26** | Safety Envelope | Link loss not detected | Flight | **Hazardous** | Link age >2s/5s, FC failsafe |
| **FC-27** | Safety Envelope | GPS fix lost not detected | Flight | **Major** | GPS fix type <3 check |
| **FC-28** | Safety Envelope | HDOP/VDOP >2 not flagged | Flight | **Minor** | DOP monitor, WARNING only |
| **FC-29** | Safety Envelope | Speed >25 m/s not limited | Flight | **Hazardous** | Speed envelope, FC authority |
| **FC-30** | Safety Envelope | Climb rate >5 m/s not limited | Flight | **Major** | Climb rate envelope |
| **FC-31** | Safety Envelope | Sink rate >3 m/s not limited | Flight | **Major** | Sink rate envelope |
| **FC-32** | Safety Envelope | Roll >40° not limited | Flight | **Major** | Attitude envelope |
| **FC-33** | Safety Envelope | Pitch >40° not limited | Flight | **Major** | Attitude envelope |
| **FC-34** | Token Gate | Token replay/reuse | All | **Catastrophic** | Single-use, 30s TTL, HTTPS/gRPC |
| **FC-35** | Token Gate | Token prediction/brute force | All | **Catastrophic** | 8-char UUID, 30s TTL |
| **FC-36** | Token Gate | Missing token on command | All | **Catastrophic** | Middleware enforces header |
| **FC-37** | Command Proxy | Unauthorized ARM/DISARM | Ground | **Catastrophic** | Token gate, FC authority |
| **FC-38** | Command Proxy | Unintended RTL/LAND | Flight | **Hazardous** | Token gate, FC authority |
| **FC-39** | Command Proxy | Command injection (MAVLink inject) | All | **Hazardous** | Input validation, FC authority |
| **FC-40** | Health/Watchdog | Watchdog fails to detect dead MAVLink task | Flight | **Hazardous** | Task monitor, task restart |
| **FC-41** | Health/Watchdog | Watchdog fails to detect dead CRSF task | Flight | **Hazardous** | Task monitor, task restart |
| **FC-42** | Health/Watchdog | Decision engine hang (>30s) | Flight | **Major** | Decision timestamp monitor |
| **FC-43** | Resource | OOM kill during flight | Flight | **Major** | MemoryMax=2G, CPUQuota=200% |
| **FC-44** | Resource | CPU saturation (>90%) | Flight | **Major** | CPUQuota=200%, watchdog |
| **FC-44** | Resource | Disk full (logs) | Flight | **Minor** | Log rotation, size limits |
| **FC-45** | gRPC/HTTP | gRPC server crash | Flight | **Major** | Process isolation, HTTP fallback |
| **FC-46** | gRPC/HTTP | gRPC stream backpressure | Flight | **Minor** | Flow control, interval min 20ms |

## Severity Summary

| Severity | Count | Functions Affected |
|----------|-------|-------------------|
| Catastrophic | 4 | Token gate, command proxy |
| Hazardous | 14 | Telemetry, advisory, envelope |
| Major | 10 | State est, envelope, commands |
| Minor | 5 | DOP, logging, backpressure |
| No Effect | 0 | - |

## Mitigation Coverage

| Mitigation | Covers FCs |
|------------|------------|
| Watchdog (MAVLink 2s, CRSF 5s) | FC-01, FC-02, FC-40, FC-41 |
| Safety Envelope (all checks) | FC-11..13, FC-19..20, FC-22..33 |
| Token Gate (single-use, 30s TTL, 8-char UUID) | FC-34, FC-35, FC-36 |
| Mode Awareness | FC-14, FC-15, FC-16, FC-17 |
| Watchdog Task Monitor | FC-40, FC-41, FC-42 |
| Resource Limits (MemoryMax, CPUQuota) | FC-43, FC-44 |
| gRPC/HTTP Separation | FC-45 |
| gRPC Flow Control | FC-46 |

## Gaps / Open Items

| Gap | Risk | Action |
|-----|------|--------|
| Common cause failure (Steam Deck HW) | Medium | FC independent, pilot manual override documented |
| Sensor spoofing (GPS spoof) | Medium | Not in scope (experimental) |
| MAVLink injection via serial | Low | FC authority, physical access required |
| Thermal throttling (Steam Deck) | Medium | CPUQuota, thermal monitoring not implemented |

---
*Document version: 0.1.0 | Based on ARP4761/ISO 26262 lite for experimental UAS*