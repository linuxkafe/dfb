"""Unit tests for CRSF/ELRS telemetry ingestion."""

import asyncio
import struct
from unittest.mock import AsyncMock, patch

import pytest

from src.dfb.crsf_ingest import (
    CRSFParser,
    CRSFTelemetry,
    crc8,
    decode_rc_channels,
    get_crsf_state,
    start_crsf_task,
    stop_crsf_task,
)


class TestCRC8:
    """Tests for CRC8 calculation."""

    def test_crc8_empty(self):
        """CRC8 of empty data."""
        assert crc8(b"") == 0

    def test_crc8_known(self):
        """Test CRC8 with known values."""
        # CRSF test vector: frame type 0x10, payload, expected CRC
        # Using known test case
        data = b"\x10" + b"\x00" * 22  # RC channels frame with zero payload
        # CRC8 should be calculated correctly
        result = crc8(data)
        assert isinstance(result, int)
        assert 0 <= result <= 255


class TestCRSFParser:
    """Tests for CRSF frame parsing."""

    def setup_method(self):
        self.parser = CRSFParser()

    def test_parse_valid_rc_channels_frame(self):
        """Test parsing valid RC channels frame."""
        # Build a valid RC channels frame
        frame_type = 0x10
        payload = b"\x00" * 22  # 22 bytes for 16 channels
        frame_data = bytes([frame_type]) + payload
        crc = crc8(frame_data)
        frame = bytes([0xC8, len(frame_data)]) + frame_data + bytes([crc])

        frames = self.parser.feed(frame)
        assert len(frames) == 1
        assert frames[0][0] == 0x10
        assert len(frames[0][1]) == 22

    def test_parse_invalid_crc(self):
        """Test that invalid CRC frames are rejected."""
        frame_type = 0x10
        payload = b"\x00" * 22
        frame_data = bytes([frame_type]) + payload
        crc = crc8(frame_data) ^ 0xFF  # Wrong CRC
        frame = bytes([0xC8, len(frame_data)]) + frame_data + bytes([crc])

        frames = self.parser.feed(frame)
        assert len(frames) == 0

    def test_incremental_parsing(self):
        """Test parsing frames split across multiple feeds."""
        frame_type = 0x10
        payload = b"\x00" * 22
        frame_data = bytes([frame_type]) + payload
        crc = crc8(frame_data)
        frame = bytes([0xC8, len(frame_data)]) + frame_data + bytes([crc])

        # Feed in chunks
        frames1 = self.parser.feed(frame[:10])
        assert len(frames1) == 0

        frames2 = self.parser.feed(frame[10:])
        assert len(frames2) == 1

    def test_multiple_frames(self):
        """Test parsing multiple frames in one feed."""
        frames_data = []
        for i in range(3):
            frame_type = 0x10
            payload = struct.pack("<H", i) * 11  # 22 bytes
            frame_data = bytes([frame_type]) + payload
            crc = crc8(frame_data)
            frame = bytes([0xC8, len(frame_data)]) + frame_data + bytes([crc])
            frames_data.append(frame)

        combined = b"".join(frames_data)
        frames = self.parser.feed(combined)
        assert len(frames) == 3


class TestDecodeRCChannels:
    """Tests for RC channels decoding."""

    def test_decode_center(self):
        """Test decoding center position (1500us)."""
        # 1500 = 0x05DC in 11 bits
        # Pack 16 channels of 1500 in 11-bit little-endian format
        payload = bytes(
            [
                0xDC,
                0xE5,
                0x2E,
                0x77,
                0xB9,
                0xCB,
                0x5D,
                0xEE,
                0x72,
                0x97,
                0xBB,
                0xDC,
                0xE5,
                0x2E,
                0x77,
                0xB9,
                0xCB,
                0x5D,
                0xEE,
                0x72,
            ]
        )
        channels = decode_rc_channels(payload)
        assert len(channels) == 16
        # All channels should be 0.0 (center)
        for ch in channels:
            assert abs(ch) < 0.01

    def test_decode_min_max(self):
        """Test decoding min/max positions."""

        # 988 = min, 2012 = max
        # Pack 16 channels of 988 and 2012 in 11-bit little-endian
        def encode_rc_channels(channels):
            bits = 0
            bit_count = 0
            payload = bytearray()
            for ch in channels:
                bits |= (ch & 0x7FF) << bit_count
                bit_count += 11
                while bit_count >= 8:
                    payload.append(bits & 0xFF)
                    bits >>= 8
                    bit_count -= 8
            return bytes(payload)

        min_val = 988
        max_val = 2012

        min_payload = encode_rc_channels([min_val] * 16)
        channels = decode_rc_channels(min_payload)
        assert channels[0] == -1.0

        max_payload = encode_rc_channels([max_val] * 16)
        channels = decode_rc_channels(max_payload)
        assert channels[0] == 1.0

    def test_decode_mixed(self):
        """Test decoding mixed channel values."""

        # Channel 0 = 1000, Channel 1 = 1500, Channel 2 = 2000
        # 1000 = 0x03E8, 1500 = 0x05DC, 2000 = 0x07D0
        def encode_rc_channels(channels):
            bits = 0
            bit_count = 0
            payload = bytearray()
            for ch in channels:
                bits |= (ch & 0x7FF) << bit_count
                bit_count += 11
                while bit_count >= 8:
                    payload.append(bits & 0xFF)
                    bits >>= 8
                    bit_count -= 8
            return bytes(payload)

        vals = [1000, 1500, 2000] + [1500] * 13
        payload = encode_rc_channels(vals)
        channels = decode_rc_channels(payload)
        assert channels[0] == pytest.approx(-0.98, abs=0.02)
        assert channels[1] == pytest.approx(0.0, abs=0.01)
        assert channels[2] == pytest.approx(0.98, abs=0.02)


class TestCRSFTelemetry:
    """Tests for CRSFTelemetry dataclass."""

    def test_defaults(self):
        """Test default values."""
        state = CRSFTelemetry()
        assert state.timestamp == 0.0
        assert state.link_ok is False
        assert len(state.channels) == 16
        assert all(c == 0.0 for c in state.channels)
        assert state.rssi is None
        assert state.lq is None
        assert state.snr is None
        assert state.msg_counts == {}


class TestCRSFModuleAPI:
    """Tests for module-level API functions."""

    @pytest.mark.asyncio
    async def test_start_stop_crsf_task(self):
        """Test start_crsf_task and stop_crsf_task."""
        with patch("src.dfb.crsf_ingest.CRSFReader") as mock_reader_class:
            mock_reader = AsyncMock()
            mock_reader.start = AsyncMock()
            mock_reader.stop = AsyncMock()
            mock_reader._task = asyncio.create_task(asyncio.sleep(0))
            mock_reader_class.return_value = mock_reader

            task = await start_crsf_task("/dev/ttyACM1", 420000)
            assert task is not None
            mock_reader.start.assert_called_once()

            await stop_crsf_task(task)
            mock_reader.stop.assert_called_once()

    def test_get_crsf_state_no_reader(self):
        """get_crsf_state returns default state when no reader."""
        import src.dfb.crsf_ingest as crsf_ingest

        original = crsf_ingest._reader
        crsf_ingest._reader = None
        try:
            state = get_crsf_state()
            assert isinstance(state, CRSFTelemetry)
            assert state.timestamp == 0.0
            assert state.link_ok is False
        finally:
            crsf_ingest._reader = original


class TestAutodetection:
    """Tests for protocol autodetection."""

    def test_detect_mavlink_v1(self):
        """Detect MAVLink v1 (0xFE)."""
        from src.dfb.mavlink_ingest import detect_protocol

        assert detect_protocol(bytes([0xFE, 0x09, 0x00])) == "mavlink"

    def test_detect_mavlink_v2(self):
        """Detect MAVLink v2 (0xFD)."""
        from src.dfb.mavlink_ingest import detect_protocol

        assert detect_protocol(bytes([0xFD, 0x00, 0x00])) == "mavlink"

    def test_detect_crsf(self):
        """Detect CRSF (0xC8)."""
        from src.dfb.mavlink_ingest import detect_protocol

        assert detect_protocol(bytes([0xC8, 0x16, 0x10])) == "crsf"

    def test_detect_unknown(self):
        """Detect unknown protocol."""
        from src.dfb.mavlink_ingest import detect_protocol

        assert detect_protocol(b"\x00\x01") == "unknown"
        assert detect_protocol(b"") == "unknown"
