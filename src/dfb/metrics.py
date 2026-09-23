"""Prometheus metrics for Deck Fly Brain."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total HTTP requests", ["endpoint", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["endpoint"]
)

# MAVLink metrics
MAVLINK_MESSAGES_TOTAL = Counter(
    "mavlink_messages_total", "Total MAVLink messages received", ["msg_type"]
)

MAVLINK_MSG_RATE = Gauge("mavlink_msg_rate_hz", "MAVLink message rate in Hz")

MAVLINK_LINK_STATUS = Gauge("mavlink_link_status", "MAVLink link status (1=ok, 0=lost)")

# CRSF metrics
CRSF_FRAMES_TOTAL = Counter(
    "crsf_frames_total", "Total CRSF frames received", ["frame_type"]
)

CRSF_CRC_ERRORS = Counter("crsf_crc_errors_total", "Total CRSF CRC errors")

CRSF_MSG_RATE = Gauge("crsf_msg_rate_hz", "CRSF message rate in Hz")

CRSF_LINK_STATUS = Gauge("crsf_link_status", "CRSF link status (1=ok, 0=lost)")

CRSF_RSSI = Gauge("crsf_rssi_dbm", "CRSF RSSI in dBm")

CRSF_LQ = Gauge("crsf_link_quality_percent", "CRSF link quality percentage")

CRSF_SNR = Gauge("crsf_snr_db", "CRSF SNR in dB")

# Decision metrics
DECISION_LATENCY = Histogram(
    "decision_latency_seconds", "Decision latency in seconds", ["mode"]
)

DECISIONS_TOTAL = Counter("decisions_total", "Total decisions made", ["mode", "action"])

# Safety metrics
SAFETY_VIOLATIONS = Counter(
    "safety_violations_total", "Total safety violations", ["category", "severity"]
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


def record_crsf_frame(frame_type: int):
    """Record CRSF frame received."""
    CRSF_FRAMES_TOTAL.labels(frame_type=str(frame_type)).inc()


def record_crsf_crc_error():
    """Record CRSF CRC error."""
    CRSF_CRC_ERRORS.inc()


def update_crsf_rate(rate_hz: float):
    """Update CRSF message rate gauge."""
    CRSF_MSG_RATE.set(rate_hz)


def update_crsf_link_status(ok: bool):
    """Update CRSF link status gauge."""
    CRSF_LINK_STATUS.set(1 if ok else 0)


def update_crsf_rssi(rssi: float):
    """Update CRSF RSSI gauge."""
    CRSF_RSSI.set(rssi)


def update_crsf_lq(lq: float):
    """Update CRSF link quality gauge."""
    CRSF_LQ.set(lq)


def update_crsf_snr(snr: float):
    """Update CRSF SNR gauge."""
    CRSF_SNR.set(snr)


def record_decision(mode: str, action: str, latency: float):
    """Record decision metrics."""
    DECISION_LATENCY.labels(mode=mode).observe(latency)
    DECISIONS_TOTAL.labels(mode=mode, action=action).inc()


def record_safety_violation(category: str, severity: str):
    """Record safety violation."""
    SAFETY_VIOLATIONS.labels(category=category, severity=severity).inc()


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
