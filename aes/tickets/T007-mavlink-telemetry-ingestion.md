---
ticket: T007
title: MAVLink telemetry ingestion pipeline on Steam Deck
sprint: sprint-02
priority: high
status: pending
created: 2026-09-19
---

# T007 — MAVLink Telemetry Ingestion Pipeline

## Acceptance Criteria

1. **MAVLink connection**: Service on Steam Deck establishes MAVLink connection to flight controller via serial (USB/FTDI) or UDP
2. **Message parsing**: Ingests and parses key MAVLink messages (HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, RC_CHANNELS, BATTERY_STATUS)
3. **Internal state**: Maintains current flight state (position, attitude, velocity, battery, RC inputs) in thread-safe structure
4. **Telemetry API**: Exposes `/telemetry` endpoint returning latest parsed state as JSON
5. **Connection resilience**: Auto-reconnect on link loss; graceful degradation (stale data flag)
6. **Rate limiting**: Configurable message rate limits to avoid overwhelming the link
7. **Tests**: Unit tests for parser, integration test with MAVLink simulator (mavproxy/SITL)

## Scope

- **In**: MAVLink v2 parser (pymavlink), serial/UDP transport, state store, REST endpoint, reconnection logic
- **Out**: CRSF/ELRS (T010), decision logic (T008), gRPC API (T011)

## Dependencies

- pymavlink (already in pyproject.toml)
- pyserial for serial transport
- Existing FastAPI service scaffold (T001, T003)

## References

- docs/REQUIREMENTS.md REQ-8, REQ-10
- src/dfb/service.py (existing FastAPI app)
- src/dfb/client.py (existing DeckClient)