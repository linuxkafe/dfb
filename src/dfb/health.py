"""Component health checking for Deck Fly Brain."""

import math
import time
from dataclasses import dataclass
from typing import Literal

from src.dfb.cpu_engine import get_cpu_engine
from src.dfb.crsf_ingest import get_crsf_state
from src.dfb.mavlink_ingest import get_telemetry_state


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    status: Literal["ok", "degraded", "unhealthy"]
    details: dict


def check_cpu_engine() -> ComponentHealth:
    """Check CPU decision engine health."""
    try:
        engine = get_cpu_engine()
        # Engine is healthy if initialized
        return ComponentHealth(
            status="ok", details={"initialized": engine._initialized}
        )
    except Exception as e:
        return ComponentHealth(status="unhealthy", details={"error": str(e)})


def check_mavlink_link() -> ComponentHealth:
    """Check MAVLink telemetry link health."""
    telemetry = get_telemetry_state()
    now = time.time()
    link_age = now - telemetry.timestamp if telemetry.timestamp > 0 else float("inf")

    if not telemetry.link_ok or link_age > 10.0:
        return ComponentHealth(
            status="unhealthy",
            details={
                "link_ok": telemetry.link_ok,
                "link_age_s": link_age,
                "last_msg_age_s": link_age,
                "msg_counts": telemetry.msg_counts,
            },
        )
    elif link_age > 2.0:
        return ComponentHealth(
            status="degraded",
            details={
                "link_ok": telemetry.link_ok,
                "link_age_s": link_age,
                "last_msg_age_s": link_age,
                "msg_counts": telemetry.msg_counts,
            },
        )
    else:
        return ComponentHealth(
            status="ok",
            details={
                "link_ok": telemetry.link_ok,
                "link_age_s": link_age,
                "last_msg_age_s": link_age,
                "msg_counts": telemetry.msg_counts,
            },
        )


def check_crsf_link() -> ComponentHealth:
    """Check CRSF/ELRS telemetry link health."""
    telemetry = get_crsf_state()
    now = time.time()
    link_age = now - telemetry.timestamp if telemetry.timestamp > 0 else float("inf")

    if not telemetry.link_ok or link_age > 10.0:
        return ComponentHealth(
            status="unhealthy",
            details={
                "link_ok": telemetry.link_ok,
                "link_age_s": link_age,
                "rssi": telemetry.rssi,
                "lq": telemetry.lq,
                "snr": telemetry.snr,
                "msg_counts": telemetry.msg_counts,
            },
        )
    elif link_age > 2.0:
        return ComponentHealth(
            status="degraded",
            details={
                "link_ok": telemetry.link_ok,
                "link_age_s": link_age,
                "rssi": telemetry.rssi,
                "lq": telemetry.lq,
                "snr": telemetry.snr,
                "msg_counts": telemetry.msg_counts,
            },
        )
    else:
        return ComponentHealth(
            status="ok",
            details={
                "link_ok": telemetry.link_ok,
                "link_age_s": link_age,
                "rssi": telemetry.rssi,
                "lq": telemetry.lq,
                "snr": telemetry.snr,
                "msg_counts": telemetry.msg_counts,
            },
        )


def check_decision_engine() -> ComponentHealth:
    """Check decision engine (advisor) health."""
    try:
        from src.dfb.advisor import get_advisor

        get_advisor()  # instantiation itself is the health check
        return ComponentHealth(status="ok", details={"advisor_ready": True})
    except Exception as e:
        return ComponentHealth(status="unhealthy", details={"error": str(e)})


def _json_safe(value):
    """Convert non-JSON-serialisable values (inf/nan) to None.

    A real ASGI server (uvicorn) fails to serialise non-finite floats in
    response JSON with HTTP 500. Telemetry timestamps default to 0 before the
    first message, producing float('inf') link ages — sanitise at the API
    boundary while keeping internal semantics unchanged.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def get_overall_health() -> tuple[Literal["ok", "degraded", "unhealthy"], dict]:
    """Get overall system health and component details."""
    cpu = check_cpu_engine()
    mavlink = check_mavlink_link()
    crsf = check_crsf_link()
    decision = check_decision_engine()

    components = {
        "cpu_engine": {"status": cpu.status, "details": _json_safe(cpu.details)},
        "mavlink_link": {
            "status": mavlink.status,
            "details": _json_safe(mavlink.details),
        },
        "crsf_link": {"status": crsf.status, "details": _json_safe(crsf.details)},
        "decision_engine": {
            "status": decision.status,
            "details": _json_safe(decision.details),
        },
    }

    # Determine overall status
    statuses = [cpu.status, mavlink.status, crsf.status, decision.status]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "ok"

    return overall, components
