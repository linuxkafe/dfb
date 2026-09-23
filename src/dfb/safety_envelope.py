"""Safety envelope for Deck Fly Brain.

Defines operational boundaries and checks for advisory decisions.
All advisories must pass safety checks before being issued.
"""

import math
import time
from dataclasses import dataclass, field

from src.dfb.state_estimator import EstimatedState


@dataclass
class SafetyConfig:
    """Safety envelope configuration.

    All distances in meters, altitudes in meters AGL.
    Geofence in degrees (lat/lon).
    """

    # Geofence (bounding box in degrees)
    min_lat: float = -90.0
    max_lat: float = 90.0
    min_lon: float = -180.0
    max_lon: float = 180.0

    # Altitude limits (meters AGL)
    min_alt: float = 5.0
    max_alt: float = 120.0

    # Battery reserve (percentage)
    min_battery_pct: float = 20.0

    # Link quality
    require_link_ok: bool = True
    max_link_age_s: float = 2.0

    # GPS quality
    min_gps_fix_type: int = 3  # 3D fix required
    max_hdop: float = 2.0
    max_vdop: float = 2.0

    # Speed limits (m/s)
    max_ground_speed: float = 25.0
    max_climb_rate: float = 5.0
    max_sink_rate: float = 3.0

    # Attitude limits (radians)
    max_roll: float = 0.7  # ~40 deg
    max_pitch: float = 0.7  # ~40 deg


@dataclass
class SafetyViolation:
    """Single safety violation."""

    category: str  # GEOFENCE, ALTITUDE, BATTERY, LINK, GPS, SPEED, ATTITUDE
    message: str
    severity: str  # WARNING, CRITICAL
    value: float  # Current value
    limit: float  # Limit that was exceeded


@dataclass
class SafetyStatus:
    """Result of safety check."""

    safe: bool
    violations: list[SafetyViolation] = field(default_factory=list)
    warnings: list[SafetyViolation] = field(default_factory=list)

    # Summary metrics
    battery_pct: float = 0.0
    link_ok: bool = False
    link_age_s: float = 999.0
    gps_fix_type: int = 0
    hdop: float = 99.0
    vdop: float = 99.0
    ground_speed: float = 0.0
    climb_rate: float = 0.0
    alt_agl: float = 0.0

    def add_violation(
        self, category: str, message: str, severity: str, value: float, limit: float
    ):
        """Add a violation."""
        v = SafetyViolation(category, message, severity, value, limit)
        if severity == "CRITICAL":
            self.violations.append(v)
            self.safe = False
        else:
            self.warnings.append(v)

    def get_summary(self) -> str:
        """Human-readable summary."""
        if self.safe:
            return "SAFE"
        parts = [f"{v.category}: {v.message}" for v in self.violations]
        return "VIOLATIONS: " + "; ".join(parts)


def check_safety(state: EstimatedState, config: SafetyConfig) -> SafetyStatus:
    """Check if state is within safety envelope.

    Args:
        state: Current estimated state
        config: Safety configuration

    Returns:
        SafetyStatus with violations and summary
    """
    status = SafetyStatus(safe=True)
    status.battery_pct = state._raw.remaining_pct if state._raw else 0.0
    status.link_ok = state._raw.link_ok if state._raw else False
    status.link_age_s = time.time() - state.timestamp if state.timestamp > 0 else 999.0
    status.gps_fix_type = state.gps_fix_type
    status.hdop = state.hdop
    status.vdop = state.vdop
    status.ground_speed = (state.ve**2 + state.vn**2) ** 0.5
    status.climb_rate = state.vu
    status.alt_agl = state.up

    if not state.valid:
        status.add_violation("STATE", "State estimate invalid", "CRITICAL", 0.0, 1.0)
        return status

    # Geofence check
    # Need raw lat/lon from telemetry
    if state._raw:
        lat, lon = state._raw.lat, state._raw.lon
        if not (config.min_lat <= lat <= config.max_lat):
            status.add_violation(
                "GEOFENCE",
                f"Latitude {lat:.6f} outside "
                f"[{config.min_lat:.6f}, {config.max_lat:.6f}]",
                "CRITICAL",
                lat,
                config.max_lat if lat > config.max_lat else config.min_lat,
            )
        if not (config.min_lon <= lon <= config.max_lon):
            status.add_violation(
                "GEOFENCE",
                f"Longitude {lon:.6f} outside "
                f"[{config.min_lon:.6f}, {config.max_lon:.6f}]",
                "CRITICAL",
                lon,
                config.max_lon if lon > config.max_lon else config.min_lon,
            )

    # Altitude check (AGL)
    if state.up < config.min_alt:
        status.add_violation(
            "ALTITUDE",
            f"Altitude {state.up:.1f}m below minimum {config.min_alt:.1f}m",
            "CRITICAL",
            state.up,
            config.min_alt,
        )
    if state.up > config.max_alt:
        status.add_violation(
            "ALTITUDE",
            f"Altitude {state.up:.1f}m above maximum {config.max_alt:.1f}m",
            "CRITICAL",
            state.up,
            config.max_alt,
        )

    # Battery check
    if state._raw and state._raw.remaining_pct < config.min_battery_pct:
        status.add_violation(
            "BATTERY",
            f"Battery {state._raw.remaining_pct:.1f}% below "
            f"reserve {config.min_battery_pct:.1f}%",
            "CRITICAL",
            state._raw.remaining_pct,
            config.min_battery_pct,
        )

    # Link check
    if config.require_link_ok and not status.link_ok:
        status.add_violation(
            "LINK",
            f"Link lost for {status.link_age_s:.1f}s "
            f"(max {config.max_link_age_s:.1f}s)",
            "CRITICAL",
            status.link_age_s,
            config.max_link_age_s,
        )

    # GPS quality
    if state.gps_fix_type < config.min_gps_fix_type:
        status.add_violation(
            "GPS",
            f"GPS fix type {state.gps_fix_type} below "
            f"required {config.min_gps_fix_type}",
            "CRITICAL",
            float(state.gps_fix_type),
            float(config.min_gps_fix_type),
        )
    if state.hdop > config.max_hdop:
        status.add_violation(
            "GPS",
            f"HDOP {state.hdop:.1f} above maximum {config.max_hdop:.1f}",
            "WARNING",
            state.hdop,
            config.max_hdop,
        )
    if state.vdop > config.max_vdop:
        status.add_violation(
            "GPS",
            f"VDOP {state.vdop:.1f} above maximum {config.max_vdop:.1f}",
            "WARNING",
            state.vdop,
            config.max_vdop,
        )

    # Speed limits
    if status.ground_speed > config.max_ground_speed:
        status.add_violation(
            "SPEED",
            f"Ground speed {status.ground_speed:.1f} m/s exceeds "
            f"limit {config.max_ground_speed:.1f} m/s",
            "WARNING",
            status.ground_speed,
            config.max_ground_speed,
        )

    # Climb/sink rate
    if status.climb_rate > config.max_climb_rate:
        status.add_violation(
            "SPEED",
            f"Climb rate {status.climb_rate:.1f} m/s exceeds "
            f"limit {config.max_climb_rate:.1f} m/s",
            "WARNING",
            status.climb_rate,
            config.max_climb_rate,
        )
    if status.climb_rate < -config.max_sink_rate:
        status.add_violation(
            "SPEED",
            f"Sink rate {abs(status.climb_rate):.1f} m/s exceeds "
            f"limit {config.max_sink_rate:.1f} m/s",
            "WARNING",
            abs(status.climb_rate),
            config.max_sink_rate,
        )

    # Attitude limits
    if abs(state.roll) > config.max_roll:
        status.add_violation(
            "ATTITUDE",
            f"Roll {math.degrees(state.roll):.1f} deg exceeds "
            f"limit {math.degrees(config.max_roll):.1f} deg",
            "WARNING",
            abs(state.roll),
            config.max_roll,
        )
    if abs(state.pitch) > config.max_pitch:
        status.add_violation(
            "ATTITUDE",
            f"Pitch {math.degrees(state.pitch):.1f} deg exceeds "
            f"limit {math.degrees(config.max_pitch):.1f} deg",
            "WARNING",
            abs(state.pitch),
            config.max_pitch,
        )

    return status


# Default safety config for typical FPV operations
DEFAULT_SAFETY_CONFIG = SafetyConfig(
    min_lat=-90.0,
    max_lat=90.0,
    min_lon=-180.0,
    max_lon=180.0,
    min_alt=10.0,
    max_alt=120.0,
    min_battery_pct=20.0,
    require_link_ok=True,
    max_link_age_s=2.0,
    min_gps_fix_type=3,
    max_hdop=2.0,
    max_vdop=2.0,
    max_ground_speed=20.0,
    max_climb_rate=5.0,
    max_sink_rate=3.0,
    max_roll=0.7,
    max_pitch=0.7,
)
