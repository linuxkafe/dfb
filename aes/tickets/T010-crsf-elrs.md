---
ticket: T010
title: CRSF/ELRS support for crossfire receivers
sprint: sprint-03
priority: medium
status: pending
created: 2026-09-19
---

# T010 — CRSF/ELRS Support

## Acceptance Criteria

1. **CRSF parser**: Decodes CRSF frames (RC channels, link statistics, battery, GPS) from serial
2. **ELRS telemetry**: Parses ELRS-specific telemetry (RSSI, LQ, SNR, RF mode)
3. **Unified API**: `/telemetry` returns both MAVLink and CRSF data with source tags
4. **Failover**: If MAVLink lost, CRSF provides RC channels + link quality for safety decisions
5. **Tests**: Unit tests with captured CRSF/ELRS frames

## Scope

- **In**: CRSF frame parsing, ELRS telemetry, unified telemetry API, serial autodetection (MAVLink vs CRSF)
- **Out**: CRSF command injection (TX), frequency hopping control

## Dependencies

- T007 (telemetry infrastructure)
- pyserial (already)
- crsf-py or custom parser (evaluate)