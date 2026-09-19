"""Deck Fly Brain — public API exports."""

from src.dfb.mavlink_ingest import (
    TelemetryState,
    get_telemetry_state,
    start_mavlink_task,
    stop_mavlink_task,
)
from src.dfb.state_estimator import (
    EstimatedState,
    estimate_state,
    bearing_to,
    distance_to,
)
from src.dfb.safety_envelope import (
    SafetyConfig,
    SafetyStatus,
    SafetyViolation,
    check_safety,
    DEFAULT_SAFETY_CONFIG,
)
from src.dfb.advisor import (
    Advisor,
    Advisory,
    MissionGoal,
    get_advisor,
    DEFAULT_SAFETY_CONFIG as ADVISOR_DEFAULT_SAFETY_CONFIG,
)

__all__ = [
    # MAVLink
    "TelemetryState",
    "get_telemetry_state",
    "start_mavlink_task",
    "stop_mavlink_task",
    # State estimation
    "EstimatedState",
    "estimate_state",
    "bearing_to",
    "distance_to",
    # Safety
    "SafetyConfig",
    "SafetyStatus",
    "SafetyViolation",
    "check_safety",
    "DEFAULT_SAFETY_CONFIG",
    # Advisor
    "Advisor",
    "Advisory",
    "MissionGoal",
    "get_advisor",
    "ADVISOR_DEFAULT_SAFETY_CONFIG",
]