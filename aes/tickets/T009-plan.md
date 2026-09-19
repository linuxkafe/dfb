---
ticket: T009
phase: plan
status: done
created: 2026-09-19
tier: standard
requires:
  - aes/kanban.md
  - aes/tickets/T009-service-hardening.md
produces:
  - aes/tickets/T009-plan.md
blocked_by: ''
---

# T009 — Plan: Service Hardening

## Reconnaissance Summary

**Current service.py state:**
- FastAPI app with lifespan managing CPU engine + MAVLink task
- Endpoints: `/health`, `/version`, `/telemetry`, `/decide`, `/confirm/*`, `/command`
- `/health` returns simple `{"status": "ok", "version": "..."}` — no component status
- MAVLink task has auto-reconnect with exponential backoff (in mavlink_ingest.py)
- systemd unit (`deploy/flybrain.service`) has `Restart=on-failure` but no resource limits
- No structured logging, no metrics endpoint, no watchdog

**Dependencies to add:** `prometheus-client` for `/metrics` endpoint

## Hostile Analysis

### ASSUMPTIONS I AM MAKING:

- [KNOWN] T007 MAVLink task has `_reader_loop` with 1s timeout + reconnect loop with backoff
- [KNOWN] T008 decision engine uses advisor which checks safety envelope
- [KNOWN] systemd unit at `deploy/flybrain.service` exists with `Restart=on-failure`
- [INFERRED] Steam Deck has limited RAM (8GB shared) and CPU (4C/8T Zen2) — resource limits needed
- [INFERRED] MAVLink link loss should not crash service — graceful degradation already partially there (`link_ok=false`)
- [ASSUMED] Watchdog should monitor MAVLink task heartbeat (last message timestamp)
- [ASSUMED] Structured JSON logging to stdout → journald is sufficient for now
- [UNKNOWN] Whether prometheus-client works well with uvicorn/FastAPI (should be fine)

### WHAT WAS NOT SPECIFIED (that matters):

- Exact component names for `/health` component status
- Metrics to expose (request latency, MAVLink msg rates, decision latency, etc.)
- Watchdog interval and restart threshold
- Memory/CPU limits for systemd (Deck has 8GB RAM, 4C/8T)

### ALTERNATIVES NOT CHOSEN:

| Option | Reason |
|--------|--------|
| Jaeger/OpenTelemetry tracing | Out of scope per ticket; structured logs with correlation IDs sufficient |
| External alerting (Prometheus Alertmanager) | Out of scope; metrics exposure sufficient |
| Custom watchdog process | In-process watchdog simpler; systemd already restarts on crash |

### RISKS AND SIDE EFFECTS:

1. **Resource limits too aggressive** → OOM kills or CPU throttling during peak load
2. **Watchdog false positives** → Restarting healthy MAVLink task breaks telemetry
3. **Metrics cardinality** → Label explosion if not careful (e.g., per-message-type counters)
4. **Log volume** → Structured JSON every request may be noisy; sample or level-based

### COST OF BEING WRONG: MEDIUM

- Service crash = loss of telemetry + advisory (but FC remains authority)
- False watchdog restart = brief telemetry gap
- Resource limits wrong = either no protection or false OOM

### SCOPE BOUNDARY:

**In**: Component health, `/metrics` (Prometheus), watchdog, systemd limits, structured logging, graceful degradation verification
**Out**: Distributed tracing, alerting, dashboard, custom systemd watchdog unit

### INVITATION FOR CONTRADICTION:

What if MAVLink reconnect loop hangs? — Watchdog should detect stale `_state.timestamp` and restart task. What if CPU engine hangs? — Track last decision timestamp.

## Technical Approach

### 1. Enhanced `/health` endpoint

Return component status object:
```json
{
  "status": "ok|degraded|unhealthy",
  "version": "0.1.0",
  "components": {
    "cpu_engine": {"status": "ok", "last_decision_ms_ago": 123},
    "mavlink_link": {"status": "ok", "last_msg_ms_ago": 45, "msg_rate_hz": 12.3},
    "decision_engine": {"status": "ok", "last_advisory_ms_ago": 67}
  }
}
```

### 2. `/metrics` endpoint (Prometheus)

Use `prometheus-client`:
- `http_requests_total` (counter, by endpoint, status)
- `http_request_duration_seconds` (histogram, by endpoint)
- `mavlink_messages_total` (counter, by msg_type)
- `mavlink_msg_rate_hz` (gauge)
- `decision_latency_seconds` (histogram, by mode)
- `mavlink_link_status` (gauge: 0/1)
- `process_cpu_seconds_total`, `process_resident_memory_bytes` (from prometheus_client.process_collector)

### 3. Watchdog task

Add to lifespan:
- Periodic (every 5s) check of:
  - MAVLink task alive (`_reader._task` not done)
  - MAVLink link freshness (`time.time() - telemetry.timestamp < 10s`)
  - CPU engine responsive (track last decision time)
- If MAVLink task dead → restart via `stop_mavlink_task` + `start_mavlink_task`
- Log warning with correlation ID

### 4. Structured logging

- Use `structlog` or stdlib `logging` with JSON formatter
- Add correlation ID middleware (generate UUID per request)
- Log: request start/end, latency, status, component health changes

### 5. systemd hardening

Update `deploy/flybrain.service`:
```ini
MemoryMax=2G
CPUQuota=200%
Restart=on-failure
RestartSec=5
```

### 6. Graceful degradation verification

- `/telemetry` already returns `link_ok=false` when stale
- Ensure no exceptions propagate from MAVLink reader

## Affected Files

| File | Operation | Description |
|------|-----------|-------------|
| `src/dfb/service.py` | modify | Enhanced `/health`, add `/metrics`, watchdog in lifespan, structured logging middleware |
| `src/dfb/health.py` | create | Component health checking logic |
| `src/dfb/metrics.py` | create | Prometheus metrics setup |
| `src/dfb/logging.py` | create | Structured JSON logging setup |
| `deploy/flybrain.service` | modify | Add MemoryMax, CPUQuota |
| `pyproject.toml` | modify | Add `prometheus-client`, `structlog` deps |
| `tests/test_health.py` | create | Unit tests for health, metrics, watchdog |

## Specification

### Health Component Status

```python
@dataclass
class ComponentHealth:
    status: Literal["ok", "degraded", "unhealthy"]
    details: dict

def check_cpu_engine() -> ComponentHealth: ...
def check_mavlink_link() -> ComponentHealth: ...
def check_decision_engine() -> ComponentHealth: ...
```

### Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

HTTP_REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['endpoint', 'status'])
HTTP_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])
MAVLINK_MSGS = Counter('mavlink_messages_total', 'MAVLink messages received', ['msg_type'])
MAVLINK_RATE = Gauge('mavlink_msg_rate_hz', 'MAVLink message rate')
DECISION_LATENCY = Histogram('decision_latency_seconds', 'Decision latency', ['mode'])
LINK_STATUS = Gauge('mavlink_link_status', 'MAVLink link status (0/1)')
```

### Watchdog

```python
async def watchdog_task():
    while True:
        await asyncio.sleep(5)
        # Check MAVLink task
        # Check link freshness
        # Restart if needed
```

## Testing Strategy

**Unit tests** (`tests/test_health.py`):
- `test_health_endpoint_components` — all three components reported
- `test_health_degraded_on_link_loss` — status "degraded" when MAVLink stale
- `test_metrics_endpoint_format` — Prometheus text format valid
- `test_metrics_counters_increment` — request counters work
- `test_watchdog_restarts_dead_task` — mock dead task, verify restart
- `test_structured_logging` — correlation ID in logs

**Chaos tests** (marked `@pytest.mark.chaos`):
- `test_mavlink_kill_recovery` — kill connection, verify auto-reconnect
- `test_oom_protection` — simulate memory pressure (skip in CI)

## Verification Criteria

- [ ] `make check` passes (all tests, lint, coverage ≥80% for new code)
- [ ] `/health` returns component statuses (cpu_engine, mavlink_link, decision_engine)
- [ ] `/metrics` returns valid Prometheus format with expected metrics
- [ ] MAVLink link loss → service stays up, `/telemetry` shows `link_ok=false`
- [ ] systemd unit has MemoryMax=2G, CPUQuota=200%
- [ ] Structured JSON logs with correlation IDs appear in journal
- [ ] Watchdog restarts dead MAVLink task (tested via mock)
- [ ] No regressions in existing endpoints

## Estimation

- Complexity: **medium** (2–8h)
- Risk: **medium** (watchdog false positives, resource limit tuning)
- Blocking dependencies: **no** (T007, T008 complete)