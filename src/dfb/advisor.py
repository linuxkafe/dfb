"""Advisory decision engine for Deck Fly Brain.

Converts estimated state + mission goal into continuous advisory outputs
(heading, altitude, speed) with safety envelope enforcement.
"""
from dataclasses import dataclass, field
from typing import Optional
import math

from src.dfb.state_estimator import EstimatedState, bearing_to
from src.dfb.safety_envelope import SafetyConfig, SafetyStatus, check_safety, DEFAULT_SAFETY_CONFIG


@dataclass
class MissionGoal:
    """Mission goal for advisory computation."""
    target_lat: Optional[float] = None      # Target latitude (degrees)
    target_lon: Optional[float] = None      # Target longitude (degrees)
    target_alt: float = 50.0                # Target altitude AGL (meters)
    target_speed: float = 10.0              # Target ground speed (m/s)
    loiter_radius: float = 50.0             # Loiter radius (meters)


@dataclass
class Advisory:
    """Continuous advisory output for flight controller.

    FC remains authority - this is advisory only.
    """
    heading_deg: float          # 0-360, true north
    altitude_m: float           # Target altitude AGL (meters)
    speed_mps: float            # Target ground speed (m/s)
    mode: str                   # Suggested FC mode: GUIDED, LOITER, RTL, etc.
    reason: str                 # Human-readable explanation

    # Metadata
    safety: Optional[SafetyStatus] = None
    distance_to_target: Optional[float] = None
    bearing_to_target: Optional[float] = None


# Modes where advisory is appropriate
ADVISORY_COMPATIBLE_MODES = {
    "GUIDED", "AUTO", "LOITER", "POSHOLD", "ALT_HOLD", "AUTO_MISSION",
}

# Modes where advisory should NOT be given (pilot in control)
MANUAL_MODES = {
    "MANUAL", "ACRO", "SPORT", "STABILIZE", "RATTITUDE", "THROW", "DRIFT",
}

# Modes that are emergency/automatic
AUTO_SAFETY_MODES = {"RTL", "LAND", "SMART_RTL", "AUTO_LAND", "AUTO_RTL", "AUTO_PRECLAND"}


def _mode_allows_advisory(mode: str) -> bool:
    """Check if FC mode allows external advisory."""
    return mode in ADVISORY_COMPATIBLE_MODES


def _is_manual_mode(mode: str) -> bool:
    """Check if mode is manual pilot control."""
    return mode in MANUAL_MODES


def _is_auto_safety_mode(mode: str) -> bool:
    """Check if mode is automatic safety mode."""
    return mode in AUTO_SAFETY_MODES


class Advisor:
    """Advisory decision engine with safety envelope."""

    def __init__(
        self,
        safety_config: SafetyConfig = DEFAULT_SAFETY_CONFIG,
        default_goal: Optional[MissionGoal] = None,
    ):
        self.safety_config = safety_config
        self.default_goal = default_goal or MissionGoal()
        self._home_position: Optional[tuple[float, float]] = None

    def set_home(self, lat: float, lon: float):
        """Set home position for relative navigation."""
        self._home_position = (lat, lon)

    def advise(
        self,
        state: EstimatedState,
        goal: Optional[MissionGoal] = None,
    ) -> Advisory:
        """Compute advisory for current state and goal.

        Args:
            state: Current estimated state (ENU frame)
            goal: Mission goal (uses default if None)

        Returns:
            Advisory with heading, altitude, speed, mode, reason
        """
        goal = goal or self.default_goal

        # 1. Check safety envelope
        safety = check_safety(state, self.safety_config)

        # 2. If safety violations, force RTL
        if not safety.safe:
            return Advisory(
                heading_deg=self._rtl_heading(state),
                altitude_m=max(state.up, self.safety_config.min_alt + 10.0),
                speed_mps=self.default_goal.target_speed,
                mode="RTL",
                reason=f"Safety violation: {safety.get_summary()}",
                safety=safety,
            )

        # 3. Check FC mode compatibility
        if _is_auto_safety_mode(state.flight_mode):
            # FC already in safety mode - don't interfere
            return Advisory(
                heading_deg=0.0,
                altitude_m=state.up,
                speed_mps=0.0,
                mode=state.flight_mode,
                reason=f"FC in automatic safety mode: {state.flight_mode}",
                safety=safety,
            )

        if _is_manual_mode(state.flight_mode):
            # Pilot in control - advisory only, no mode change
            heading, alt, speed, reason = self._compute_advisory(state, goal)
            return Advisory(
                heading_deg=heading,
                altitude_m=alt,
                speed_mps=speed,
                mode="ADVISORY",  # Special mode indicating advisory only
                reason=reason + " (pilot in control)",
                safety=safety,
            )

        if not _mode_allows_advisory(state.flight_mode):
            # Unknown or unsupported mode
            return Advisory(
                heading_deg=0.0,
                altitude_m=state.up,
                speed_mps=0.0,
                mode=state.flight_mode,
                reason=f"FC mode not compatible with advisory: {state.flight_mode}",
                safety=safety,
            )

        # 4. Compute advisory for compatible auto modes
        heading, alt, speed, reason = self._compute_advisory(state, goal)

        return Advisory(
            heading_deg=heading,
            altitude_m=alt,
            speed_mps=speed,
            mode="GUIDED",
            reason=reason,
            safety=safety,
        )

    def _compute_advisory(
        self,
        state: EstimatedState,
        goal: MissionGoal,
    ) -> tuple[float, float, float, str]:
        """Compute heading, altitude, speed for goal.

        Returns:
            (heading_deg, altitude_m, speed_mps, reason)
        """
        # Default to current state if no goal
        if goal.target_lat is None or goal.target_lon is None:
            return (
                math.degrees(state.yaw) % 360.0,
                max(state.up, self.safety_config.min_alt),
                min(self.default_goal.target_speed, self.safety_config.max_ground_speed),
                "No target set - maintaining current heading",
            )

        # Need raw lat/lon for bearing calculation
        if not state._raw:
            return (
                math.degrees(state.yaw) % 360.0,
                goal.target_alt,
                self.default_goal.target_speed,
                "No GPS data - using defaults",
            )

        # Compute bearing to target
        bearing = bearing_to(
            goal.target_lat, goal.target_lon,
            state._raw.lat, state._raw.lon,
        )

        # Compute distance
        from src.dfb.state_estimator import distance_to
        dist = distance_to(
            goal.target_lat, goal.target_lon,
            state._raw.lat, state._raw.lon,
        )

        # If close to target, loiter
        if dist < goal.loiter_radius:
            return (
                bearing,
                goal.target_alt,
                0.0,
                f"At target ({dist:.1f}m) - loitering",
            )

        # Normal navigation
        # Clamp altitude to safety limits
        alt = max(self.safety_config.min_alt, min(goal.target_alt, self.safety_config.max_alt))

        # Clamp speed
        speed = min(goal.target_speed, self.safety_config.max_ground_speed)

        return (
            bearing,
            alt,
            speed,
            f"Navigating to target ({dist:.1f}m away)",
        )

    def _rtl_heading(self, state: EstimatedState) -> float:
        """Compute heading for RTL (return to home)."""
        if self._home_position and state._raw:
            return bearing_to(
                self._home_position[0], self._home_position[1],
                state._raw.lat, state._raw.lon,
            )
        # Default: current heading
        return math.degrees(state.yaw) % 360.0


# Global advisor instance
_advisor: Optional[Advisor] = None


def get_advisor(
    safety_config: SafetyConfig = DEFAULT_SAFETY_CONFIG,
    default_goal: Optional[MissionGoal] = None,
) -> Advisor:
    """Get or create global advisor instance."""
    global _advisor
    if _advisor is None:
        _advisor = Advisor(safety_config, default_goal)
    return _advisor


def set_advisor(advisor: Advisor):
    """Set global advisor instance (for testing)."""
    global _advisor
    _advisor = advisor