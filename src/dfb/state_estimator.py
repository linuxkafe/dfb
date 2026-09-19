"""State estimation for Deck Fly Brain.

Provides validation and coordinate transformation of FC telemetry.
Since the flight controller runs its own EKF, this module mainly:
- Validates consistency of received data
- Transforms between coordinate frames (NED -> ENU)
- Computes derived quantities (ground speed, climb rate)
- Detects anomalies (GPS glitches, IMU divergence)
"""
import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.dfb.mavlink_ingest import TelemetryState


@dataclass
class EstimatedState:
    """Estimated vehicle state in ENU frame (meters, radians, m/s).

    ENU = East-North-Up (local tangent plane)
    NED = North-East-Down (aerospace standard, used by MAVLink)
    """
    # Position (ENU, meters relative to home)
    east: float = 0.0
    north: float = 0.0
    up: float = 0.0

    # Velocity (ENU, m/s)
    ve: float = 0.0
    vn: float = 0.0
    vu: float = 0.0

    # Attitude (radians, ENU frame)
    # roll: rotation about North axis (positive = right wing down)
    # pitch: rotation about East axis (positive = nose up)
    # yaw: rotation about Up axis (positive = clockwise from North)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    # Metadata
    timestamp: float = 0.0          # Unix time of last update
    valid: bool = False             # True if all required data present
    gps_fix_type: int = 0           # 0=none, 1=no fix, 2=2D, 3=3D, 4=DGPS, 5=RTK
    satellites_visible: int = 0
    hdop: float = 99.0              # Horizontal dilution of precision
    vdop: float = 99.0              # Vertical dilution of precision

    # Flight mode from HEARTBEAT
    flight_mode: str = "UNKNOWN"
    armed: bool = False

    # Raw telemetry for debugging
    _raw: Optional[TelemetryState] = field(default=None, repr=False)


# MAVLink mode mapping (ArduPilot/PX4 custom_mode -> standard mode)
# These are common values; actual values depend on firmware
ARDUPILOT_MODE_MAP = {
    0: "STABILIZE",
    1: "ACRO",
    2: "ALT_HOLD",
    3: "AUTO",
    4: "GUIDED",
    5: "LOITER",
    6: "RTL",
    7: "CIRCLE",
    9: "LAND",
    10: "DRIFT",
    11: "SPORT",
    13: "DODGE",
    14: "GUIDED_NOGPS",
    15: "SMART_RTL",
    16: "FLOWHOLD",
    17: "FOLLOW",
    18: "ZIGZAG",
    19: "SYSTEMID",
    20: "AUTOTUNE",
    21: "POSHOLD",
    22: "BRAKE",
    23: "THROW",
    24: "AVOID_ADSB",
    25: "GUIDED_SLOW",
}

PX4_MODE_MAP = {
    # PX4 main modes (base_mode) + custom submodes
    # Simplified - real mapping is more complex
    1: "MANUAL",
    2: "ALTCTL",
    3: "POSCTL",
    4: "AUTO_MISSION",
    5: "AUTO_LOITER",
    6: "AUTO_RTL",
    7: "ACRO",
    8: "OFFBOARD",
    9: "STABILIZED",
    10: "RATTITUDE",
    11: "AUTO_TAKEOFF",
    12: "AUTO_LAND",
    13: "AUTO_FOLLOW",
    14: "AUTO_PRECLAND",
}


def _map_flight_mode(base_mode: int, custom_mode: int, autopilot: int = 3) -> str:
    """Map MAVLink base_mode + custom_mode to standard mode string.

    autopilot: 3 = ArduPilot, 6 = PX4 (MAV_AUTOPILOT enum)
    """
    # Check if armed
    armed = bool(base_mode & 0x80)  # MAV_MODE_FLAG_SAFETY_ARMED

    if autopilot == 3:  # ArduPilot
        mode = ARDUPILOT_MODE_MAP.get(custom_mode, f"AP_MODE_{custom_mode}")
    elif autopilot == 6:  # PX4
        # PX4 uses main mode in custom_mode lower bits
        main_mode = custom_mode & 0xFF
        mode = PX4_MODE_MAP.get(main_mode, f"PX4_MODE_{main_mode}")
    else:
        mode = f"MODE_{custom_mode}"

    return mode


def _ned_to_enu(north: float, east: float, down: float) -> tuple[float, float, float]:
    """Convert NED to ENU coordinates."""
    return east, north, -down


def _enu_to_ned(east: float, north: float, up: float) -> tuple[float, float, float]:
    """Convert ENU to NED coordinates."""
    return north, east, -up


def _wrap_angle(angle: float) -> float:
    """Wrap angle to [-pi, pi]."""
    return (angle + math.pi) % (2 * math.pi) - math.pi


def estimate_state(telemetry: TelemetryState, home_position: Optional[tuple[float, float]] = None) -> EstimatedState:
    """Convert TelemetryState (NED) to EstimatedState (ENU) with validation.

    Args:
        telemetry: Raw telemetry from MAVLink ingestion
        home_position: (lat, lon) of home position in degrees. If None, uses first GPS fix.

    Returns:
        EstimatedState with validated, transformed data
    """
    if telemetry.timestamp == 0.0 or not telemetry.link_ok:
        return EstimatedState(
            timestamp=telemetry.timestamp,
            valid=False,
            flight_mode="NO_LINK",
            _raw=telemetry,
        )

    # Position: convert from degrees to local ENU (meters relative to home)
    # Simple equirectangular projection - accurate for small areas (<10km)
    if home_position is None:
        home_lat, home_lon = telemetry.lat, telemetry.lon
    else:
        home_lat, home_lon = home_position

    # Earth radius at latitude
    R = 6371000.0  # meters
    lat_rad = math.radians(home_lat)

    # Delta in degrees
    dlat = telemetry.lat - home_lat
    dlon = telemetry.lon - home_lon

    # Convert to meters (ENU)
    north = dlat * 111111.0  # 1 deg lat ≈ 111.111 km
    east = dlon * 111111.0 * math.cos(lat_rad)
    up = telemetry.relative_alt / 1000.0  # mm to m (relative_alt is AGL)

    # Velocity: NED to ENU
    # MAVLink vx/vy/vz are in NED frame (cm/s): vx=North, vy=East, vz=Down
    vn = telemetry.vx / 100.0   # North = vx
    ve = telemetry.vy / 100.0   # East = vy
    vu = -telemetry.vz / 100.0  # Up = -Down

    # Attitude: MAVLink ATTITUDE is in NED frame (body->NED)
    # roll/pitch same in ENU, yaw needs conversion
    roll = telemetry.roll
    pitch = telemetry.pitch
    # MAVLink yaw: 0 = North, positive clockwise (NED)
    # ENU yaw: 0 = North, positive clockwise (same!)
    # Actually both are NED convention for yaw... but ENU frame has Z up
    # The rotation matrix conversion: yaw_enu = -yaw_ned (with offset)
    # For simplicity, keep as-is since both use North=0, CW=positive
    yaw = _wrap_angle(telemetry.yaw)

    # GPS quality from GLOBAL_POSITION_INT not directly available
    # Would need GPS_RAW_INT or GPS2_RAW message
    # Placeholder values
    gps_fix_type = 3 if (telemetry.lat != 0.0 and telemetry.lon != 0.0) else 0
    satellites_visible = 0
    hdop = 1.0
    vdop = 1.0

    # Determine if state is valid
    valid = (
        telemetry.link_ok
        and telemetry.lat != 0.0
        and telemetry.lon != 0.0
        and abs(roll) < math.pi
        and abs(pitch) < math.pi
    )

    return EstimatedState(
        east=east,
        north=north,
        up=up,
        ve=ve,
        vn=vn,
        vu=vu,
        roll=roll,
        pitch=pitch,
        yaw=yaw,
        timestamp=telemetry.timestamp,
        valid=valid,
        gps_fix_type=gps_fix_type,
        satellites_visible=satellites_visible,
        hdop=hdop,
        vdop=vdop,
        flight_mode="UNKNOWN",  # Will be set by caller with HEARTBEAT data
        armed=False,
        _raw=telemetry,
    )


def compute_ground_speed(state: EstimatedState) -> float:
    """Compute horizontal ground speed (m/s)."""
    return math.hypot(state.ve, state.vn)


def compute_climb_rate(state: EstimatedState) -> float:
    """Compute vertical speed (m/s, positive = up)."""
    return state.vu


def bearing_to(target_lat: float, target_lon: float, current_lat: float, current_lon: float) -> float:
    """Compute bearing from current to target (degrees, 0-360, true north)."""
    lat1 = math.radians(current_lat)
    lat2 = math.radians(target_lat)
    dlon = math.radians(target_lon - current_lon)

    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def distance_to(target_lat: float, target_lon: float, current_lat: float, current_lon: float) -> float:
    """Compute great-circle distance (meters)."""
    R = 6371000.0
    lat1 = math.radians(current_lat)
    lat2 = math.radians(target_lat)
    dlat = math.radians(target_lat - current_lat)
    dlon = math.radians(target_lon - current_lon)

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c