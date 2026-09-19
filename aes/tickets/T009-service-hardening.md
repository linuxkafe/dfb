---
ticket: T009
title: Service hardening: auto-restart, graceful degradation, health checks
sprint: sprint-02
priority: medium
status: pending
created: 2026-09-19
---

# T009 — Service Hardening

## Acceptance Criteria

1. **Health checks**: `/health` returns component status (cpu_engine, mavlink_link, decision_engine) not just "ok"
2. **Graceful degradation**: Service stays up if MAVLink link lost; `/telemetry` returns stale data with `link_ok=false`
3. **Auto-restart**: systemd `Restart=on-failure` verified; MAVLink task auto-reconnects with backoff
4. **Resource limits**: systemd `MemoryMax`, `CPUQuota` set to protect Deck
5. **Watchdog**: Background task health monitored; restart task if stuck
6. **Logging**: Structured JSON logs to journald; correlation IDs for request tracing
7. **Metrics**: `/metrics` endpoint (Prometheus format) for CPU, memory, MAVLink msg rates, decision latency
8. **Tests**: Chaos tests (kill MAVLink, OOM, CPU stress) verify degradation not crash

## Scope

- **In**: Enhanced `/health`, `/metrics`, watchdog, systemd hardening, structured logging
- **Out**: Distributed tracing (Jaeger), alerting, dashboard

## Dependencies

- T007 (MAVLink task to monitor)
- T008 (decision engine to monitor)
- prometheus-client (new dep)

## References

- docs/REQUIREMENTS.md REQ-17, REQ-20
- deploy/flybrain.service (systemd unit)
- src/dfb/service.py