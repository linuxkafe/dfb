# Safety Documentation

## Overview
This directory contains all safety certification artifacts for the Deck Fly Brain (DFB) system. These artifacts collectively form the safety case demonstrating that residual risk is acceptable for experimental flight operations.

## Document Index

| Document | Description | Standard | Status |
|----------|-------------|----------|--------|
| [ssa.md](ssa.md) | System Safety Assessment | ARP4761 / ISO 26262 lite | ✅ Complete |
| [fha.md](fha.md) | Functional Hazard Analysis | ARP4761 | ✅ Complete |
| [fta.md](fta.md) | Fault Tree Analysis | ARP4761 | ✅ Complete |
| [traceability.md](traceability.md) | Traceability Matrix | ARP4761 | ✅ Complete |
| [case.md](case.md) | Safety Case (GSN) | GSN / ISO 15504 | ✅ Complete |
| [operational_limits.md](operational_limits.md) | Operational Limits | - | ✅ Complete |
| [emergency.md](emergency.md) | Emergency Procedures | - | ✅ Complete |

## Document Status

| Document | Version | Last Updated | Status |
|----------|---------|--------------|--------|
| ssa.md | 0.1.0 | 2026-09-20 | ✅ Complete |
| fha.md | 0.1.0 | 2026-09-20 | ✅ Complete |
| fta.md | 0.1.0 | 2026-09-20 | ✅ Complete |
| traceability.md | 0.1.0 | 2026-09-20 | ✅ Complete |
| case.md | 0.1.0 | 2026-09-20 | ✅ Complete |
| operational_limits.md | 0.1.0 | 2026-09-20 | ✅ Complete |
| emergency.md | 0.1.0 | 2026-09-20 | ✅ Complete |

## Safety Case Summary

### Goal
**G0**: Residual risk acceptable for experimental flight operations

### Strategy
Defense in depth with 5 independent layers:

| Layer | Description | Key Evidence |
|-------|-------------|--------------|
| 1 | FC remains ultimate authority | REQ-19, architecture diagram |
| 2 | Advisory constrained by safety envelope | FHA mitigations, test_advisor.py |
| 3 | Commands require explicit confirmation | Token gate, test_client.py |
| 4 | Link loss detected and handled | Watchdog, test_health.py |
| 5 | System fails safe | Graceful degradation, no command on link loss |

## Verification Checklist

- [x] SSA documents system, environment, safety requirements
- [x] FHA identifies ≥10 failure conditions with severity classification
- [x] FTA analyzes ≥4 top events with minimal cut sets
- [x] Traceability matrix covers all REQs → Hazards → Tests
- [x] Safety Case (GSN) argues residual risk acceptable
- [x] Operational Limits documented with configurable parameters
- [x] Emergency Procedures cover 6 scenarios
- [ ] All artifacts reviewed and approved
- [ ] CI gate: `make safety-check` passes

## Maintenance

### Review Cycle
- **Per Release**: All artifacts reviewed for accuracy
- **Per Sprint**: Traceability matrix updated
- **Quarterly**: Full safety case review

### Update Procedure
1. Modify artifact in `docs/safety/`
2. Update traceability matrix if hazards/requirements change
3. Run `make safety-check`
4. Peer review via PR
5. Update version in document header

## CI Gates

```bash
# Run all safety checks
make safety-check

# Specific checks
make safety-check-traceability
make safety-check-consistency
make safety-check-completeness
```

## References

- ARP4761 - Guidelines and Methods for Conducting Safety Assessment Process on Civil Airborne Systems and Equipment
- ISO 26262 - Road vehicles - Functional safety (lite adaptation)
- MIL-STD-882E - Standard Practice for System Safety
- GSN Community Standard - Goal Structuring Notation

## Contact

For safety documentation questions, contact the DFB safety team via GitHub issues.