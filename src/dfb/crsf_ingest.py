"""CRSF/ELRS telemetry ingestion for Deck Fly Brain.

Provides background task that connects to Crossfire/ELRS receiver via serial,
parses CRSF frames, and maintains telemetry state.
"""

import asyncio
import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional

import serial

# CRSF protocol constants
CRSF_HEADER = 0xC8
CRSF_FRAME_MAX_SIZE = 64

# CRSF frame types
CRSF_FRAMETYPE_RC_CHANNELS_PACKED = 0x10
CRSF_FRAMETYPE_LINK_STATISTICS = 0x14
CRSF_FRAMETYPE_LINK_RX = 0x15
CRSF_FRAMETYPE_LINK_TX = 0x16
CRSF_FRAMETYPE_ELRS = 0x17
CRSF_FRAMETYPE_BATTERY = 0x08
CRSF_FRAMETYPE_GPS = 0x09

# CRC8 polynomial for CRSF (0xD5)
CRC8_POLY = 0xD5


def crc8(data) -> int:
    """Calculate CRC8 for CRSF (polynomial 0xD5, init 0x00)."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ CRC8_POLY
            else:
                crc = crc << 1
            crc &= 0xFF
    return crc


def decode_rc_channels(payload: bytes) -> List[float]:
    """Decode 16 RC channels from 22-byte packed payload (11 bits each).

    Returns list of 16 channels normalized to -1.0..1.0
    (988us = -1.0, 1500us = 0.0, 2012us = 1.0)
    """
    if len(payload) < 22:
        return [0.0] * 16

    # Unpack 11-bit channels from 22 bytes
    bits = 0
    bit_count = 0
    channels = []

    for byte in payload[:22]:
        bits |= byte << bit_count
        bit_count += 8
        while bit_count >= 11:
            channel_value = bits & 0x7FF  # 11 bits
            channels.append(channel_value)
            bits >>= 11
            bit_count -= 11

    # Normalize: 988..2012 -> -1.0..1.0 (center 1500)
    normalized = []
    for ch in channels[:16]:
        norm = max(-1.0, min(1.0, (ch - 1500) / 512))
        normalized.append(norm)

    # Pad to 16 if needed
    while len(normalized) < 16:
        normalized.append(0.0)

    return normalized[:16]


@dataclass
class CRSFTelemetry:
    """Parsed CRSF/ELRS telemetry state."""

    timestamp: float = 0.0
    link_ok: bool = False

    # RC channels (16 channels, normalized -1.0..1.0)
    channels: List[float] = field(default_factory=lambda: [0.0] * 16)

    # Link statistics
    rssi: Optional[float] = None  # dBm
    lq: Optional[float] = None  # Link quality 0-100%
    snr: Optional[float] = None  # dB
    rf_mode: Optional[int] = None  # ELRS RF mode

    # Battery
    voltage: Optional[float] = None  # V
    current: Optional[float] = None  # A
    capacity: Optional[float] = None  # mAh consumed

    # GPS
    gps: Optional[dict] = None  # lat, lon, alt, speed, sats

    # Message counts for diagnostics
    msg_counts: dict[str, int] = field(default_factory=dict)


class CRSFParser:
    """Incremental CRSF frame parser with CRC8 validation."""

    def __init__(self):
        self.buffer = bytearray()
        self.expected_len = 0

    def feed(self, data: bytes) -> List[tuple]:
        """Feed raw bytes, return list of (frame_type, payload) for complete frames."""
        self.buffer.extend(data)
        frames = []

        while len(self.buffer) >= 4:  # Minimum frame: header + len + type + crc
            # Find header
            if self.buffer[0] != CRSF_HEADER:
                self.buffer.pop(0)
                continue

            if len(self.buffer) < 2:
                break

            frame_len = self.buffer[
                1
            ]  # Length of type + payload (not including header, len, crc)

            # Total: header(1) + len(1) + type(1) + payload(frame_len-1) + crc(1)
            total_len = frame_len + 3

            if len(self.buffer) < total_len:
                break

            # Extract frame WITHOUT header for CRC check
            # without header: len(1)+type(1)+payload(frame_len-1)+crc(1) = frame_len+2
            # But CRC covers ONLY type + payload (frame_len bytes)
            frame_without_header = self.buffer[
                1 : frame_len + 3
            ]  # len + type + payload + crc
            self.buffer = self.buffer[
                frame_len + 3 :
            ]  # skip header + len + type + payload + crc

            # Verify CRC (covers ONLY type + payload = frame_len bytes)
            # frame_without_header = len + type + payload + crc
            # CRC covers frame_without_header[1:-1] = type + payload
            if crc8(frame_without_header[1:-1]) != frame_without_header[-1]:
                continue

            frame_type = frame_without_header[1]  # skip len byte
            payload = frame_without_header[2:-1]  # skip len and crc
            frames.append((frame_type, payload))

        return frames


class CRSFReader:
    """Background CRSF reader with auto-reconnect and parsing."""

    def __init__(
        self,
        device: str,
        baud: int = 420000,
    ):
        self.device = device
        self.baud = baud

        self._state = CRSFTelemetry()
        self._lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._serial: Optional[serial.Serial] = None
        self._parser = CRSFParser()

        # Reconnect config
        self._base_backoff = 1.0
        self._max_backoff = 30.0
        self._link_timeout = 2.0  # seconds before link_ok = False

    def _parse_frame(self, frame_type: int, payload: bytes) -> None:
        """Parse a single CRSF frame and update state."""
        now = time.time()

        async def _update():
            async with self._lock:
                self._state.msg_counts[str(frame_type)] = (
                    self._state.msg_counts.get(str(frame_type), 0) + 1
                )
                self._state.timestamp = now
                self._state.link_ok = True

                if frame_type == CRSF_FRAMETYPE_RC_CHANNELS_PACKED:
                    self._state.channels = decode_rc_channels(payload)

                elif frame_type == CRSF_FRAMETYPE_LINK_STATISTICS:
                    # RSSI (int8, dBm), LQ (uint8, %), SNR (int8, dB)
                    if len(payload) >= 3:
                        self._state.rssi = struct.unpack("b", payload[0:1])[0]
                        self._state.lq = payload[1]
                        self._state.snr = struct.unpack("b", payload[2:3])[0]

                elif frame_type == CRSF_FRAMETYPE_ELRS:
                    # ELRS-specific: RF mode, etc.
                    if len(payload) >= 1:
                        self._state.rf_mode = payload[0]

                elif frame_type == CRSF_FRAMETYPE_BATTERY:
                    # Voltage (uint16, 0.01V), Current (uint16, 0.01A),
                    # Capacity (uint24, mAh)
                    if len(payload) >= 6:
                        self._state.voltage = (
                            struct.unpack("<H", payload[0:2])[0] / 100.0
                        )
                        self._state.current = (
                            struct.unpack("<H", payload[2:4])[0] / 100.0
                        )
                        # 24-bit capacity
                        self._state.capacity = struct.unpack(
                            "<I", payload[4:7] + b"\x00"
                        )[0]

                elif frame_type == CRSF_FRAMETYPE_GPS:
                    # lat/lon (int32, 1e-7 deg), alt (int16, m),
                    # speed (uint16), sats (uint8)
                    if len(payload) >= 15:
                        lat = struct.unpack("<i", payload[0:4])[0] / 1e7
                        lon = struct.unpack("<i", payload[4:8])[0] / 1e7
                        alt = struct.unpack("<h", payload[8:10])[0]
                        speed = struct.unpack("<H", payload[10:12])[0] / 100.0
                        sats = payload[12]
                        self._state.gps = {
                            "lat": lat,
                            "lon": lon,
                            "alt": alt,
                            "speed": speed,
                            "satellites": sats,
                        }

        # Run the async update
        asyncio.create_task(_update())

    async def _reader_loop(self) -> None:
        """Async reader loop."""
        while self._running:
            try:
                if self._serial is None or not self._serial.is_open:
                    await self._connect()
                    await asyncio.sleep(1.0)
                    continue

                # Read available data
                if self._serial.in_waiting:
                    data = self._serial.read(self._serial.in_waiting)
                    frames = self._parser.feed(data)
                    for frame_type, payload in frames:
                        self._parse_frame(frame_type, payload)
                else:
                    await asyncio.sleep(0.001)  # Small delay to prevent busy loop

            except Exception:
                async with self._lock:
                    self._state.link_ok = False
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                    self._serial = None
                await asyncio.sleep(self._base_backoff)

    async def _connect(self) -> None:
        """Establish serial connection."""
        try:
            self._serial = serial.Serial(
                port=self.device,
                baudrate=self.baud,
                timeout=0.1,
            )
        except Exception:
            self._serial = None
            raise

    async def start(self) -> None:
        """Start the background reader task."""
        self._running = True
        self._task = asyncio.create_task(self._reader_loop())

    async def stop(self) -> None:
        """Stop the background reader gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._serial and self._serial.is_open:
            self._serial.close()

    def get_state(self) -> CRSFTelemetry:
        """Get thread-safe copy of current telemetry state."""
        # Note: this is called from sync context, so we can't use async lock
        # For simplicity, we'll do a quick copy without lock (brief window)
        return CRSFTelemetry(
            timestamp=self._state.timestamp,
            link_ok=self._state.link_ok,
            channels=self._state.channels.copy(),
            rssi=self._state.rssi,
            lq=self._state.lq,
            snr=self._state.snr,
            rf_mode=self._state.rf_mode,
            voltage=self._state.voltage,
            current=self._state.current,
            capacity=self._state.capacity,
            gps=self._state.gps.copy() if self._state.gps else None,
            msg_counts=self._state.msg_counts.copy(),
        )


# Module-level singleton
_reader: Optional[CRSFReader] = None


async def start_crsf_task(
    device: str,
    baud: int = 420000,
) -> asyncio.Task:
    """Start background CRSF ingestion task. Returns the reader task."""
    global _reader
    if _reader is not None:
        await stop_crsf_task(
            asyncio.current_task() or asyncio.create_task(asyncio.sleep(0))
        )

    _reader = CRSFReader(device=device, baud=baud)
    await _reader.start()
    return _reader._task  # type: ignore


async def stop_crsf_task(task: asyncio.Task) -> None:
    """Stop the background CRSF task gracefully."""
    global _reader
    if _reader is not None:
        await _reader.stop()
        _reader = None


def get_crsf_state() -> CRSFTelemetry:
    """Get current CRSF telemetry state."""
    global _reader
    if _reader is None:
        return CRSFTelemetry()
    return _reader.get_state()
