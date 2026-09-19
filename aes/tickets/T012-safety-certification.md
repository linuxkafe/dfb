---
ticket: T012
title: Safety certification artifacts (hazard analysis, test reports)
sprint: sprint-03
priority: high
status: pending
created: 2026-09-19
---

# T012 — Safety Certification Artifacts

## Acceptance Criteria

1. **System Safety Assessment (SSA)**: Document per ARP4761/ISO 26262 lite — functions, hazards, mitigations
2. **Functional Hazard Analysis (FHA)**: Identify failure conditions, classify severity (Catastrophic, Hazardous, Major, Minor, No Effect)
3. **Fault Tree Analysis (FTA)**: Top-down analysis for critical hazards (unintended command, lost link, wrong decision)
4. **Test Evidence**: Traceability matrix linking requirements → hazards → tests → results
5. **Safety Case**: Structured argument (GSN or CAE) that residual risk is acceptable for experimental use
6. **Operational Limits**: Documented envelope (geofence, altitude, battery, weather, link budget)
7. **Emergency Procedures**: Documented pilot takeover, RTL trigger, kill switch procedures

## Scope

- **In**: SSA, FHA, FTA, test traceability, safety case, operational limits, emergency procedures
- **Out**: DO-178C/DO-254 full certification (not applicable), flight test campaign (separate)

## Dependencies

- T007, T008, T009 (system must be functional to analyze)
- All existing tests (evidence)

## References

- docs/REQUIREMENTS.md REQ-19 (FC firmware never modified)
- AES safety gate (token confirmation)
- ARP4761, ISO 26262, MIL-STD-882E (reference standards)