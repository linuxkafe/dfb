"""Deck Fly Brain — public API exports."""

from src.dfb.crsf_ingest import (
    CRSFTelemetry,
    get_crsf_state,
    start_crsf_task,
    stop_crsf_task,
)
from src.dfb.mavlink_ingest import (
    TelemetryState,
    detect_protocol,
    get_telemetry_state,
    start_mavlink_task,
    stop_mavlink_task,
)
from src.dfb.state_estimator import (
    EstimatedState,
    estimate_state,
    estimate_state_fused,
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
    # CRSF
    "CRSFTelemetry",
    "get_crsf_state",
    "start_crsf_task",
    "stop_crsf_task",
    # MAVLink
    "TelemetryState",
    "detect_protocol",
    "get_telemetry_state",
    "start_mavlink_task",
    "stop_mavlink_task",
    # State estimation
    "EstimatedState",
    "estimate_state",
    "estimate_state_fused",
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