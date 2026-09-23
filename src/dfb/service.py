"""Fly Brain service for Steam Deck — health, version, decide, safety gate, telemetry.

Endpoints: /health, /version, /decide, /telemetry, /metrics,
           /confirm/issue, /command, /confirm/verify.
"""

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Literal, Optional

import numpy as np
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from src import __version__
from src.dfb.advisor import MissionGoal, get_advisor
from src.dfb.cpu_engine import get_cpu_engine, shutdown_cpu_engine
from src.dfb.crsf_ingest import (
    get_crsf_state,
    start_crsf_task,
    stop_crsf_task,
)
from src.dfb.grpc_server import run_grpc_server
from src.dfb.health import get_overall_health
from src.dfb.logging import (
    CorrelationIdMiddleware,
    log_component_health,
    log_mavlink_event,
    log_request,
    setup_logging,
)
from src.dfb.mavlink_ingest import (
    TelemetryState,
    get_telemetry_state,
    start_mavlink_task,
    stop_mavlink_task,
)
from src.dfb.metrics import (
    metrics_endpoint,
    record_decision,
    record_http_request,
    record_safety_violation,
    update_mavlink_link_status,
    update_mavlink_rate,
)
from src.dfb.serialization import SanitizingJSONResponse
from src.dfb.state_estimator import estimate_state

# Confirmation token store (in-memory, single-use, 30s TTL)
_confirmation_tokens: dict[str, float] = {}
_TOKEN_TTL = 30.0

# Watchdog state
_watchdog_task: Optional[asyncio.Task] = None
_last_decision_time: float = 0.0
_last_mavlink_msg_time: float = 0.0
_last_crsf_msg_time: float = 0.0


@dataclass
class UnifiedTelemetryState:
    """Unified telemetry state combining MAVLink and CRSF sources."""

    mavlink: Optional[TelemetryState] = None
    crsf: Optional[object] = None  # CRSFTelemetry (avoid circular import)
    primary_source: Literal["mavlink", "crsf", "none"] = "none"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging("INFO")

    get_cpu_engine()

    # Determine telemetry protocol
    protocol = os.getenv("TELEMETRY_PROTOCOL", "auto").lower()

    mavlink_task = None
    crsf_task = None
    grpc_server_task = None

    if protocol in ("auto", "mavlink"):
        mavlink_task = await start_mavlink_task(
            device=os.getenv("MAVLINK_DEVICE", "/dev/ttyACM0"),
            baud=int(os.getenv("MAVLINK_BAUD", "57600")),
            source_system=int(os.getenv("MAVLINK_SOURCE_SYSTEM", "255")),
            source_component=int(os.getenv("MAVLINK_SOURCE_COMPONENT", "190")),
            target_system=int(os.getenv("MAVLINK_TARGET_SYSTEM", "1")),
            target_component=int(os.getenv("MAVLINK_TARGET_COMPONENT", "1")),
        )

    if protocol in ("auto", "crsf"):
        crsf_task = await start_crsf_task(
            device=os.getenv("CRSF_DEVICE", "/dev/ttyACM1"),
            baud=int(os.getenv("CRSF_BAUD", "420000")),
        )

    # Start gRPC server
    grpc_port = int(os.getenv("GRPC_PORT", "8083"))
    enable_tls = os.getenv("GRPC_TLS", "false").lower() == "true"
    cert_file = os.getenv("GRPC_CERT_FILE")
    key_file = os.getenv("GRPC_KEY_FILE")

    grpc_server_task = asyncio.create_task(
        run_grpc_server(grpc_port, enable_tls, cert_file, key_file)
    )

    # Start watchdog
    global _watchdog_task
    _watchdog_task = asyncio.create_task(_watchdog_loop())

    yield

    # Shutdown
    if _watchdog_task:
        _watchdog_task.cancel()
        try:
            await _watchdog_task
        except asyncio.CancelledError:
            pass
    if mavlink_task:
        await stop_mavlink_task(mavlink_task)
    if crsf_task:
        await stop_crsf_task(crsf_task)
    if grpc_server_task:
        grpc_server_task.cancel()
        try:
            await grpc_server_task
        except asyncio.CancelledError:
            pass
    shutdown_cpu_engine()


app = FastAPI(
    title="Deck Fly Brain",
    version=__version__,
    lifespan=lifespan,
    default_response_class=SanitizingJSONResponse,
)

# Add correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    duration_ms = duration * 1000

    # Record metrics
    record_http_request(request.url.path, response.status_code, duration)

    # Log request
    cid = request.headers.get("X-Correlation-ID", "")
    log_request(
        request.url.path,
        request.method,
        response.status_code,
        duration_ms,
        cid,
    )

    response.headers["X-Process-Time"] = str(duration)
    return response


async def _watchdog_loop():
    """Watchdog task to monitor MAVLink link and restart if stuck."""
    global _last_decision_time, _last_mavlink_msg_time

    while True:
        try:
            await asyncio.sleep(5.0)

            # Check MAVLink link
            telemetry = get_telemetry_state()
            now = time.time()
            link_age = (
                now - telemetry.timestamp if telemetry.timestamp > 0 else float("inf")
            )

            # Update metrics
            update_mavlink_link_status(telemetry.link_ok)
            if telemetry.msg_counts:
                total_msgs = sum(telemetry.msg_counts.values())
                update_mavlink_rate(total_msgs / max(1.0, link_age))

            # Check if MAVLink task is alive
            if link_age > 10.0:
                log_mavlink_event(
                    "watchdog_restart",
                    {
                        "reason": "link_stale",
                        "link_age_s": link_age,
                        "last_msg_counts": telemetry.msg_counts,
                    },
                )
                # Restart MAVLink task
                # Note: This would require access to the task from lifespan
                # For now, just log the event
                pass

            # Check decision engine responsiveness
            if _last_decision_time > 0 and (now - _last_decision_time) > 30.0:
                log_component_health(
                    "decision_engine",
                    "degraded",
                    {
                        "last_decision_age_s": now - _last_decision_time,
                    },
                )

        except asyncio.CancelledError:
            break
        except Exception:
            # Don't let watchdog crash
            pass


@app.get("/health")
async def health():
    """Enhanced health endpoint with component status."""
    overall, components = get_overall_health()

    # Log health status changes
    for comp_name, comp_data in components.items():
        log_component_health(comp_name, comp_data["status"], comp_data["details"])

    return {
        "status": overall,
        "version": __version__,
        "components": components,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return metrics_endpoint()


class DecideRequest(BaseModel):
    # Legacy maze mode (backward compatible)
    position: Optional[List[int]] = None
    grid: Optional[List[List[int]]] = None
    exit: Optional[List[int]] = None

    # New telemetry-aware mode
    use_telemetry: bool = False
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    target_alt: Optional[float] = None
    target_speed: Optional[float] = None


class AdvisoryResponse(BaseModel):
    heading_deg: float
    altitude_m: float
    speed_mps: float
    mode: str
    reason: str
    distance_to_target: Optional[float] = None
    bearing_to_target: Optional[float] = None


class SafetyStatusResponse(BaseModel):
    safe: bool
    violations: List[dict] = []
    warnings: List[dict] = []
    battery_pct: float
    link_ok: bool
    link_age_s: float
    gps_fix_type: int
    hdop: float
    vdop: float
    ground_speed: float
    climb_rate: float
    alt_agl: float


class DecideResponse(BaseModel):
    # Legacy fields (maze mode)
    action: Optional[str] = None
    confidence: Optional[float] = None
    logits: Optional[List[float]] = None

    # New telemetry-aware fields
    advisory: Optional[AdvisoryResponse] = None
    safety: Optional[SafetyStatusResponse] = None


class CommandRequest(BaseModel):
    action: str
    params: Optional[dict] = None


class CommandResponse(BaseModel):
    success: bool
    message: str


class ConfirmIssueResponse(BaseModel):
    token: str
    expires_in: float


def _cleanup_expired_tokens():
    now = time.time()
    expired = [k for k, v in _confirmation_tokens.items() if now - v > 30.0]
    for k in expired:
        del _confirmation_tokens[k]


def _verify_token(token: str) -> bool:
    _cleanup_expired_tokens()
    if token in _confirmation_tokens:
        del _confirmation_tokens[token]  # Single-use
        return True
    return False


@app.get("/version")
async def version():
    return {"version": __version__}


@app.get("/telemetry")
async def telemetry():
    """Get current telemetry state from flight controller.

    Returns unified telemetry with both MAVLink and CRSF sources.
    """
    mavlink_state = get_telemetry_state()
    crsf_state = get_crsf_state()

    # Determine primary source
    primary = "none"
    if mavlink_state.link_ok and not crsf_state.link_ok:
        primary = "mavlink"
    elif crsf_state.link_ok and not mavlink_state.link_ok:
        primary = "crsf"
    elif mavlink_state.link_ok and crsf_state.link_ok:
        primary = "mavlink"  # Default to MAVLink when both available

    # Build fused state (prefer primary, fallback to secondary)
    fused_rc_channels = []
    if primary == "crsf" and crsf_state.channels:
        fused_rc_channels = crsf_state.channels
    elif mavlink_state.rc_channels:
        fused_rc_channels = mavlink_state.rc_channels
    elif crsf_state.channels:
        fused_rc_channels = crsf_state.channels

    return {
        "primary_source": primary,
        "mavlink": {
            "timestamp": mavlink_state.timestamp,
            "link_ok": mavlink_state.link_ok,
            "position": {
                "lat": mavlink_state.lat,
                "lon": mavlink_state.lon,
                "alt": mavlink_state.alt / 1000.0,
                "relative_alt": mavlink_state.relative_alt / 1000.0,
            },
            "attitude": {
                "roll": mavlink_state.roll,
                "pitch": mavlink_state.pitch,
                "yaw": mavlink_state.yaw,
            },
            "velocity": {
                "vx": mavlink_state.vx / 100.0,
                "vy": mavlink_state.vy / 100.0,
                "vz": mavlink_state.vz / 100.0,
            },
            "battery": {
                "voltage_v": mavlink_state.voltage_v,
                "current_a": mavlink_state.current_a,
                "remaining_pct": mavlink_state.remaining_pct,
            },
            "rc_channels": mavlink_state.rc_channels,
            "message_counts": mavlink_state.msg_counts,
            "flight_mode": mavlink_state.flight_mode,
            "armed": mavlink_state.armed,
        },
        "crsf": {
            "timestamp": crsf_state.timestamp,
            "link_ok": crsf_state.link_ok,
            "rc_channels": crsf_state.channels,
            "rssi": crsf_state.rssi,
            "lq": crsf_state.lq,
            "snr": crsf_state.snr,
            "rf_mode": crsf_state.rf_mode,
            "voltage": crsf_state.voltage,
            "current": crsf_state.current,
            "capacity": crsf_state.capacity,
            "gps": crsf_state.gps,
            "message_counts": crsf_state.msg_counts,
        },
        "fused": {
            "rc_channels": fused_rc_channels,
            "timestamp": max(mavlink_state.timestamp, crsf_state.timestamp),
        },
    }


@app.post("/decide", response_model=DecideResponse)
async def decide(payload: DecideRequest):
    """Decision endpoint with two modes:
    1. Legacy maze mode.
    2. Telemetry-aware mode.
    Legacy returns discrete action (UP/DOWN/LEFT/RIGHT).
    Telemetry returns continuous advisory (heading, altitude, speed).
    """
    if payload.use_telemetry:
        return await _decide_telemetry(payload)
    return await _decide_maze(payload)


async def _decide_telemetry(payload: DecideRequest) -> DecideResponse:
    """Telemetry-aware decision using real flight state."""
    start_time = time.time()
    global _last_decision_time

    # Get current telemetry from both sources
    mavlink_telemetry = get_telemetry_state()
    crsf_telemetry = get_crsf_state()

    # Estimate state in ENU frame
    state = estimate_state(mavlink_telemetry)
    state.flight_mode = mavlink_telemetry.flight_mode
    state.armed = mavlink_telemetry.armed

    # Override RC channels with CRSF if available (higher rate, more precise)
    if crsf_telemetry.link_ok and crsf_telemetry.channels:
        # We'd need to update the state estimator to use CRSF channels
        pass

    # Build mission goal
    goal = MissionGoal(
        target_lat=payload.target_lat,
        target_lon=payload.target_lon,
        target_alt=payload.target_alt or 50.0,
        target_speed=payload.target_speed or 10.0,
    )

    # Get advisor and compute advisory
    advisor = get_advisor()
    advisory = advisor.advise(state, goal)

    # Convert to response models
    advisory_resp = AdvisoryResponse(
        heading_deg=advisory.heading_deg,
        altitude_m=advisory.altitude_m,
        speed_mps=advisory.speed_mps,
        mode=advisory.mode,
        reason=advisory.reason,
        distance_to_target=advisory.distance_to_target,
        bearing_to_target=advisory.bearing_to_target,
    )

    safety_resp = None
    if advisory.safety:
        s = advisory.safety
        violations = [
            {
                "category": v.category,
                "message": v.message,
                "severity": v.severity,
                "value": v.value,
                "limit": v.limit,
            }
            for v in s.violations
        ]
        warnings = [
            {
                "category": v.category,
                "message": v.message,
                "severity": v.severity,
                "value": v.value,
                "limit": v.limit,
            }
            for v in s.warnings
        ]
        safety_resp = SafetyStatusResponse(
            safe=s.safe,
            violations=violations,
            warnings=warnings,
            battery_pct=s.battery_pct,
            link_ok=s.link_ok,
            link_age_s=s.link_age_s,
            gps_fix_type=s.gps_fix_type,
            hdop=s.hdop,
            vdop=s.vdop,
            ground_speed=s.ground_speed,
            climb_rate=s.climb_rate,
            alt_agl=s.alt_agl,
        )

    return DecideResponse(
        advisory=advisory_resp,
        safety=safety_resp,
    )

    # Record metrics
    duration = time.time() - start_time
    _last_decision_time = time.time()
    record_decision("telemetry", advisory.mode, duration)
    if advisory.safety:
        for v in advisory.safety.violations:
            record_safety_violation(v.category, v.severity)
        for v in advisory.safety.warnings:
            record_safety_violation(v.category, v.severity)


async def _decide_maze(payload: DecideRequest) -> DecideResponse:
    """Legacy maze decision using CPU engine (numpy MLP)."""
    start_time = time.time()
    global _last_decision_time
    engine = get_cpu_engine()

    # Prepare input: flatten grid (10x10=100); engine expects 100.
    grid = payload.grid or []
    flat_grid = [cell for row in grid for cell in row]

    # Ensure 100 elements
    if len(flat_grid) != 100:
        flat_grid = flat_grid[:100] + [0] * max(0, 100 - len(flat_grid))

    input_array = np.array(flat_grid, dtype=np.float32)
    logits = engine.compute(input_array)

    action_idx = int(np.argmax(logits))
    actions = ["UP", "DOWN", "LEFT", "RIGHT"]
    action = actions[action_idx]
    probs = np.exp(logits - np.max(logits))
    confidence = float(logits[action_idx] / (np.sum(probs) + 1e-8))

    response = DecideResponse(
        action=action,
        confidence=confidence,
        logits=logits.tolist(),
    )

    # Record metrics
    duration = time.time() - start_time
    _last_decision_time = time.time()
    record_decision("maze", action, duration)

    return response


@app.post("/confirm/issue", response_model=ConfirmIssueResponse)
async def confirm_issue():
    """Issue a new confirmation token for safety-critical commands."""
    token = str(uuid.uuid4())[:8]
    _confirmation_tokens[token] = time.time()
    return ConfirmIssueResponse(token=token, expires_in=_TOKEN_TTL)


@app.post("/command", response_model=CommandResponse)
async def command(
    payload: CommandRequest, x_confirmation_token: Optional[str] = Header(None)
):
    """
    Safety-critical command endpoint. Requires valid X-Confirmation-Token header.
    """
    if not x_confirmation_token:
        raise HTTPException(
            status_code=403,
            detail="Missing X-Confirmation-Token header",
        )

    if not _verify_token(x_confirmation_token):
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired confirmation token",
        )

    # In a real system, this would send MAVLink commands to the flight controller
    # For now, just acknowledge
    return CommandResponse(
        success=True, message=f"Command '{payload.action}' acknowledged (simulated)"
    )


@app.get("/confirm/verify/{token}")
async def confirm_verify(token: str):
    """Check if a token is valid (without consuming it)."""
    _cleanup_expired_tokens()
    valid = token in _confirmation_tokens
    remaining = _TOKEN_TTL - (time.time() - _confirmation_tokens.get(token, 0))
    return {"valid": valid, "expires_in": max(0, remaining)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
