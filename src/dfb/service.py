"""Fly Brain service for Steam Deck — health, version, decide, safety gate, telemetry.

Endpoints: /health, /version, /decide, /telemetry,
           /confirm/issue, /command, /confirm/verify.
"""
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src import __version__
from src.dfb.cpu_engine import get_cpu_engine, shutdown_cpu_engine
from src.dfb.mavlink_ingest import (
    get_telemetry_state,
    start_mavlink_task,
    stop_mavlink_task,
)

# Confirmation token store (in-memory, single-use, 30s TTL)
_confirmation_tokens: dict[str, float] = {}
_TOKEN_TTL = 30.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    get_cpu_engine()
    mavlink_task = await start_mavlink_task(
        device=os.getenv("MAVLINK_DEVICE", "/dev/ttyACM0"),
        baud=int(os.getenv("MAVLINK_BAUD", "57600")),
        source_system=int(os.getenv("MAVLINK_SOURCE_SYSTEM", "255")),
        source_component=int(os.getenv("MAVLINK_SOURCE_COMPONENT", "190")),
        target_system=int(os.getenv("MAVLINK_TARGET_SYSTEM", "1")),
        target_component=int(os.getenv("MAVLINK_TARGET_COMPONENT", "1")),
    )
    yield
    # Shutdown
    await stop_mavlink_task(mavlink_task)
    shutdown_cpu_engine()


app = FastAPI(title="Deck Fly Brain", version=__version__, lifespan=lifespan)


class DecideRequest(BaseModel):
    position: List[int]
    grid: List[List[int]]
    exit: List[int]


class DecideResponse(BaseModel):
    action: str
    confidence: float
    logits: Optional[List[float]] = None


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


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.get("/version")
async def version():
    return {"version": __version__}


@app.get("/telemetry")
async def telemetry():
    """Get current telemetry state from flight controller.

    Returns:
    - timestamp: Unix time of last update
    - link_ok: True if received message within 2s
    - position: {lat, lon, alt, relative_alt} in degrees/meters
    - attitude: {roll, pitch, yaw} in radians
    - velocity: {vx, vy, vz} in m/s (converted from cm/s)
    - battery: {voltage_v, current_a, remaining_pct}
    - rc_channels: 16 channels normalized -1.0..1.0
    - message_counts: Dict of MAVLink message type -> count
    """
    state = get_telemetry_state()
    return {
        "timestamp": state.timestamp,
        "link_ok": state.link_ok,
        "position": {
            "lat": state.lat,
            "lon": state.lon,
            "alt": state.alt / 1000.0,  # mm to m
            "relative_alt": state.relative_alt / 1000.0,
        },
        "attitude": {
            "roll": state.roll,
            "pitch": state.pitch,
            "yaw": state.yaw,
        },
        "velocity": {
            "vx": state.vx / 100.0,  # cm/s to m/s
            "vy": state.vy / 100.0,
            "vz": state.vz / 100.0,
        },
        "battery": {
            "voltage_v": state.voltage_v,
            "current_a": state.current_a,
            "remaining_pct": state.remaining_pct,
        },
        "rc_channels": state.rc_channels,
        "message_counts": state.msg_counts,
    }


@app.post("/decide", response_model=DecideResponse)
async def decide(payload: DecideRequest):
    """
    Decision endpoint using CPU engine (numpy MLP).
    Input: {"position": [x,y], "grid": [[0,1,...]], "exit": [ex,ey]}
    Output: {"action": "UP|DOWN|LEFT|RIGHT", "confidence": float, "logits": [...]}
    """
    engine = get_cpu_engine()

    # Prepare input: flatten grid (10x10=100); engine expects 100.
    # For now, use just the grid flattened.
    grid = payload.grid
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

    return DecideResponse(action=action, confidence=confidence, logits=logits.tolist())


@app.post("/confirm/issue", response_model=ConfirmIssueResponse)
async def confirm_issue():
    """Issue a new confirmation token for safety-critical commands."""
    token = str(uuid.uuid4())[:8]
    _confirmation_tokens[token] = time.time()
    return ConfirmIssueResponse(token=token, expires_in=_TOKEN_TTL)


@app.post("/command", response_model=CommandResponse)
async def command(
    payload: CommandRequest,
    x_confirmation_token: Optional[str] = Header(None)
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
        success=True,
        message=f"Command '{payload.action}' acknowledged (simulated)"
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
