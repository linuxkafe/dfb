"""MAVLink telemetry ingestion for Deck Fly Brain.

Provides background task that connects to flight controller via MAVLink,
parses key messages, and maintains thread-safe telemetry state.
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from pymavlink import mavutil


class TelemetryReaderBase:
    """Base class for telemetry readers (MAVLink, CRSF)."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background reader task."""
        self._running = True

    async def stop(self) -> None:
        """Stop the background reader gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def is_running(self) -> bool:
        return self._running


def detect_protocol(data: bytes) -> str:
    """Detect telemetry protocol from first bytes.

    Returns: "mavlink", "crsf", or "unknown"
    """
    if not data:
        return "unknown"

    # MAVLink v1: 0xFE, MAVLink v2/signed: 0xFD
    if data[0] in (0xFE, 0xFD):
        return "mavlink"

    # CRSF: 0xC8
    if data[0] == 0xC8:
        return "crsf"

    return "unknown"


@dataclass
class TelemetryState:
    """Thread-safe container for latest telemetry from flight controller.

    All fields updated under _lock in MavlinkReader.
    Use get_telemetry_state() for atomic snapshot.
    """

    timestamp: float = 0.0  # time.time() of last update
    link_ok: bool = False  # True if received message < 2s ago

    # Position (MAVLink format: degrees * 1e7, mm)
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0  # mm, absolute
    relative_alt: float = 0.0  # mm, relative to home

    # Attitude (radians)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    # Velocity (cm/s, NED frame)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0

    # Battery
    voltage_v: float = 0.0
    current_a: float = 0.0
    remaining_pct: float = 0.0

    # RC channels (normalized -1.0..1.0)
    rc_channels: list[float] = field(default_factory=lambda: [0.0] * 16)

    # Flight mode from HEARTBEAT
    flight_mode: str = "UNKNOWN"
    armed: bool = False
    autopilot: int = 0  # MAV_AUTOPILOT enum

    # Message counts for diagnostics
    msg_counts: dict[str, int] = field(default_factory=dict)


class MavlinkReader:
    """Background MAVLink reader with auto-reconnect and parsing."""

    def __init__(
        self,
        device: str,
        baud: int,
        source_system: int = 255,
        source_component: int = 190,  # MAV_COMP_ID_ONBOARD_COMPUTER
        target_system: int = 1,
        target_component: int = 1,
    ):
        self.device = device
        self.baud = baud
        self.source_system = source_system
        self.source_component = source_component
        self.target_system = target_system
        self.target_component = target_component

        self._state = TelemetryState()
        self._lock = threading.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._connection: Optional[mavutil.mavlink_connection] = None

        # Reconnect config
        self._base_backoff = 1.0
        self._max_backoff = 30.0
        self._link_timeout = 2.0  # seconds before link_ok = False

    def _map_flight_mode(self, base_mode: int, custom_mode: int, autopilot: int) -> str:
        """Map MAVLink base_mode + custom_mode to standard mode string."""
        # ArduPilot modes
        ardupilot_modes = {
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

        # PX4 modes (simplified)
        px4_modes = {
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

        if autopilot == 3:  # ArduPilot
            return ardupilot_modes.get(custom_mode, f"AP_MODE_{custom_mode}")
        elif autopilot == 6:  # PX4
            main_mode = custom_mode & 0xFF
            return px4_modes.get(main_mode, f"PX4_MODE_{main_mode}")
        else:
            return f"MODE_{custom_mode}"

    def _make_connection(self) -> mavutil.mavlink_connection:
        """Create MAVLink connection (serial or UDP)."""
        if self.device.startswith("udp:") or self.device.startswith("tcp:"):
            # UDP/TCP connection for SITL
            conn = mavutil.mavlink_connection(
                self.device,
                source_system=self.source_system,
                source_component=self.source_component,
            )
        else:
            # Serial connection
            conn = mavutil.mavlink_connection(
                self.device,
                baud=self.baud,
                source_system=self.source_system,
                source_component=self.source_component,
            )
        return conn

    def _parse_message(self, msg) -> None:
        """Parse a single MAVLink message and update state."""
        msg_type = msg.get_type()
        now = time.time()

        with self._lock:
            self._state.msg_counts[msg_type] = (
                self._state.msg_counts.get(msg_type, 0) + 1
            )
            self._state.timestamp = now
            self._state.link_ok = True

            if msg_type == "HEARTBEAT":
                # Extract flight mode and armed status
                self._state.armed = bool(
                    msg.base_mode & 0x80
                )  # MAV_MODE_FLAG_SAFETY_ARMED
                self._state.autopilot = msg.autopilot
                self._state.flight_mode = self._map_flight_mode(
                    msg.base_mode, msg.custom_mode, msg.autopilot
                )

            elif msg_type == "ATTITUDE":
                self._state.roll = msg.roll
                self._state.pitch = msg.pitch
                self._state.yaw = msg.yaw

            elif msg_type == "GLOBAL_POSITION_INT":
                # MAVLink: lat/lon in degrees * 1e7, alt in mm
                self._state.lat = msg.lat / 1e7
                self._state.lon = msg.lon / 1e7
                self._state.alt = float(msg.alt)
                self._state.relative_alt = float(msg.relative_alt)
                self._state.vx = float(msg.vx)
                self._state.vy = float(msg.vy)
                self._state.vz = float(msg.vz)

            elif msg_type == "SYS_STATUS":
                # Voltage in mV, current in cA (centi-amps)
                self._state.voltage_v = msg.voltage_battery / 1000.0
                self._state.current_a = msg.current_battery / 100.0

            elif msg_type == "BATTERY_STATUS":
                # Remaining in percent (0-100), voltages in mV
                if msg.battery_remaining >= 0:
                    self._state.remaining_pct = float(msg.battery_remaining)
                if msg.voltages:
                    # Use first cell voltage as reference
                    self._state.voltage_v = msg.voltages[0] / 1000.0

            elif msg_type == "RC_CHANNELS":
                # Normalize PWM (typically 1000-2000) to -1..1
                for i in range(min(16, len(msg.chan_raw))):
                    pwm = getattr(msg, f"chan{i + 1}_raw", 1500)
                    self._state.rc_channels[i] = max(
                        -1.0, min(1.0, (pwm - 1500) / 500.0)
                    )

    def _reader_loop(self) -> None:
        """Blocking reader loop - runs in thread pool."""
        while self._running:
            try:
                if self._connection is None:
                    self._connection = self._make_connection()
                    # Wait for first heartbeat
                    self._connection.wait_heartbeat(timeout=10)
                    continue

                # Non-blocking receive with timeout
                msg = self._connection.recv_match(blocking=True, timeout=1.0)
                if msg:
                    self._parse_message(msg)
                else:
                    # Timeout - check link health
                    with self._lock:
                        if time.time() - self._state.timestamp > self._link_timeout:
                            self._state.link_ok = False

            except Exception:
                # Connection error - trigger reconnect
                with self._lock:
                    self._state.link_ok = False
                if self._connection:
                    self._connection.close()
                    self._connection = None
                # Backoff before retry
                time.sleep(self._base_backoff)

    async def _reconnect_loop(self) -> None:
        """Async reconnect manager with exponential backoff."""
        backoff = self._base_backoff
        while self._running:
            if self._connection is None:
                try:
                    self._connection = self._make_connection()
                    await asyncio.to_thread(self._connection.wait_heartbeat, timeout=10)
                    backoff = self._base_backoff  # Reset on success
                except Exception:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self._max_backoff)
            else:
                await asyncio.sleep(1.0)

    async def start(self) -> None:
        """Start the background reader task."""
        self._running = True
        # Run blocking reader in thread pool
        self._task = asyncio.create_task(asyncio.to_thread(self._reader_loop))
        # Also start reconnect monitor
        asyncio.create_task(self._reconnect_loop())

    async def stop(self) -> None:
        """Stop the background reader gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._connection:
            self._connection.close()
            self._connection = None

    def get_state(self) -> TelemetryState:
        """Get thread-safe copy of current telemetry state."""
        with self._lock:
            # Check link timeout
            if time.time() - self._state.timestamp > self._link_timeout:
                self._state.link_ok = False
            # Return copy to avoid external mutation
            return TelemetryState(
                timestamp=self._state.timestamp,
                link_ok=self._state.link_ok,
                lat=self._state.lat,
                lon=self._state.lon,
                alt=self._state.alt,
                relative_alt=self._state.relative_alt,
                roll=self._state.roll,
                pitch=self._state.pitch,
                yaw=self._state.yaw,
                vx=self._state.vx,
                vy=self._state.vy,
                vz=self._state.vz,
                voltage_v=self._state.voltage_v,
                current_a=self._state.current_a,
                remaining_pct=self._state.remaining_pct,
                rc_channels=self._state.rc_channels.copy(),
                flight_mode=self._state.flight_mode,
                armed=self._state.armed,
                autopilot=self._state.autopilot,
                msg_counts=self._state.msg_counts.copy(),
            )


# Module-level singleton
_reader: Optional[MavlinkReader] = None


async def start_mavlink_task(
    device: str,
    baud: int,
    source_system: int = 255,
    source_component: int = 190,
    target_system: int = 1,
    target_component: int = 1,
) -> asyncio.Task:
    """Start background MAVLink ingestion task. Returns the reader task."""
    global _reader
    if _reader is not None:
        await stop_mavlink_task(
            asyncio.current_task() or asyncio.create_task(asyncio.sleep(0))
        )

    _reader = MavlinkReader(
        device=device,
        baud=baud,
        source_system=source_system,
        source_component=source_component,
        target_system=target_system,
        target_component=target_component,
    )
    await _reader.start()
    return _reader._task  # type: ignore


async def stop_mavlink_task(task: asyncio.Task) -> None:
    """Stop the background MAVLink task gracefully."""
    global _reader
    if _reader is not None:
        await _reader.stop()
        _reader = None


def get_telemetry_state() -> TelemetryState:
    """Thread-safe getter for current telemetry state."""
    global _reader
    if _reader is None:
        return TelemetryState()
    return _reader.get_state()
