# Emergency Procedures

## Overview
This document defines emergency procedures for the Deck Fly Brain (DFB) system. All procedures assume the Flight Controller (FC) remains the ultimate authority.

## Emergency Scenarios

### 1. Link Loss (MAVLink/CRSF)

#### Detection
- MAVLink: No heartbeat received for > 2 seconds
- CRSF: Link quality < 20% for > 5 seconds

#### Procedure
1. **DFB Action**: Advisory mode = RTL (Return to Launch)
2. **Pilot Action**: Take manual control immediately
3. **FC Action**: Execute RTL failsafe (configured in FC)
4. **Recovery**: If link restored, DFB resumes advisory; pilot may resume auto

#### Escalation
- Link loss > 10s: FC executes failsafe (RTL/LAND)
- Link restored: DFB resumes advisory; pilot acknowledges

---

### 2. Wrong Advisory Issued

#### Detection
- Pilot observes incorrect advisory
- Safety envelope violation detected
- FC behavior unexpected

#### Procedure
1. **Pilot Action**: Ignore advisory, take manual control
2. **DFB Action**: Safety envelope blocks hazardous advisory
3. **Pilot Override**: Switch FC to MANUAL/STABILIZE
4. **Report**: Log incident with timestamp, advisory details, pilot action

---

### 3. Battery Critical

#### Thresholds
| Level | Threshold | Action |
|---------|-----------|--------|
| Warning | < 30% | Advisory: "Battery low, plan landing" |
| Critical | < 20% | Advisory: RTL |
| Emergency | < 10% | Immediate RTL + Land |

#### Procedure
1. **DFB Advisory**: RTL at 20%, Land at 10%
2. **Pilot**: Confirm RTL, monitor descent
3. **FC**: Executes RTL/Land per failsafe

---

### 4. Geofence Breach

#### Detection
- Position outside configured geofence
- Safety envelope CRITICAL violation

#### Procedure
1. **DFB Advisory**: RTL immediately
2. **Pilot**: Manual override if needed
3. **FC**: Executes RTL to home
4. **Post-flight**: Analyze geofence configuration

---

### 5. DFB Power Loss / Steam Deck Failure

#### Detection
- DFB service stops responding
- No telemetry updates
- gRPC/HTTP endpoints unreachable

#### DFB Power Loss
- DFB shuts down gracefully
- FC continues on its own battery
- FC executes failsafe (RTL/Land)

#### Steam Deck Failure
- FC detects loss of DFB heartbeat
- FC executes configured failsafe (RTL/Land)
- Pilot takes manual control immediately

#### Procedure
1. **Pilot**: Immediate manual control
2. **FC**: Detects DFB loss → executes failsafe (RTL/Land)
3. **Post-flight**: Inspect Steam Deck, review logs

---

### 6. Steam Deck Overheating

#### Detection
- Thermal throttling detected
- CPU throttling > 80%

#### Procedure
1. **DFB Advisory**: Reduce performance, RTL if critical
2. **Pilot**: Monitor temperature, prepare for manual
3. **Action**: Land ASAP if temperature > 85°C

---

### 7. Kill Switch Activation

#### Hardware Kill Switch
- External hardware switch (pilot accessible)
- Cuts power to motors immediately
- FC enters disarmed state

#### Software Kill Switch
- DFB `/command` with `kill` action + valid token
- Sends `MAV_CMD_DO_FLIGHTTERMINATION` to FC

---

## Emergency Contact & Escalation

| Role | Contact | When |
|-------|---------|------|
| Pilot in Command | Radio/Voice | All emergencies |
| Safety Officer | Phone/Message | Post-incident |
| DFB Developer | GitHub Issue | Bug/Regression |
| FC Vendor Support | Vendor Channel | FC firmware issue |

---

## Post-Incident Procedure

1. **Immediate**: Secure aircraft, ensure safety
2. **Log Collection**: Export DFB logs, FC logs, telemetry
3. **Timeline**: Document timeline with timestamps
4. **Root Cause**: 5 Whys analysis
5. **Corrective Action**: Code/config fix, test, deploy
6. **Review**: Update procedures, update safety artifacts
7. **Sign-off**: Pilot + Safety Officer approval

---

## Emergency Checklist (Pre-flight)

- [ ] Link check: MAVLink + CRSF both green
- [ ] Geofence: Configured and armed
- [ ] Altitude limits: Set and verified
- [ ] Battery: > 30% (20% reserve + margin)
- [ ] GPS: 3D fix, HDOP < 2.0
- [ ] Weather: VFR, wind < 15 m/s
- [ ] Pilot: Current, current, simulator current
- [ ] Kill switch: Armed and tested
- [ ] FC failsafe: RTL configured and tested
- [ ] Emergency contacts: Verified

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-09-20 | Initial version |

---

*Part of T012 Safety Certification Artifacts*