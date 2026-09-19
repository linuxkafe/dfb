"""Prometheus metrics for Deck Fly Brain."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response


# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['endpoint', 'status']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['endpoint']
)

# MAVLink metrics
MAVLINK_MESSAGES_TOTAL = Counter(
    'mavlink_messages_total',
    'Total MAVLink messages received',
    ['msg_type']
)

MAVLINK_MSG_RATE = Gauge(
    'mavlink_msg_rate_hz',
    'MAVLink message rate in Hz'
)

MAVLINK_LINK_STATUS = Gauge(
    'mavlink_link_status',
    'MAVLink link status (1=ok, 0=lost)'
)

# Decision metrics
DECISION_LATENCY = Histogram(
    'decision_latency_seconds',
    'Decision latency in seconds',
    ['mode']
)

DECISIONS_TOTAL = Counter(
    'decisions_total',
    'Total decisions made',
    ['mode', 'action']
)

# Safety metrics
SAFETY_VIOLATIONS = Counter(
    'safety_violations_total',
    'Total safety violations',
    ['category', 'severity']
)


def record_http_request(endpoint: str, status: int, duration: float):
    """Record HTTP request metrics."""
    HTTP_REQUESTS_TOTAL.labels(endpoint=endpoint, status=str(status)).inc()
    HTTP_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)


def record_mavlink_message(msg_type: str):
    """Record MAVLink message received."""
    MAVLINK_MESSAGES_TOTAL.labels(msg_type=msg_type).inc()


def update_mavlink_rate(rate_hz: float):
    """Update MAVLink message rate gauge."""
    MAVLINK_MSG_RATE.set(rate_hz)


def update_mavlink_link_status(ok: bool):
    """Update MAVLink link status gauge."""
    MAVLINK_LINK_STATUS.set(1 if ok else 0)


def record_decision(mode: str, action: str, latency: float):
    """Record decision metrics."""
    DECISION_LATENCY.labels(mode=mode).observe(latency)
    DECISIONS_TOTAL.labels(mode=mode, action=action).inc()


def record_safety_violation(category: str, severity: str):
    """Record safety violation."""
    SAFETY_VIOLATIONS.labels(category=category, severity=severity).inc()


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )