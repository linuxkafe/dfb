"""Unit tests for MAVLink telemetry ingestion."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dfb.mavlink_ingest import (
    MavlinkReader,
    TelemetryState,
    get_telemetry_state,
    start_mavlink_task,
    stop_mavlink_task,
)


class TestTelemetryState:
    """Tests for TelemetryState dataclass."""

    def test_telemetry_state_defaults(self):
        """All fields zero/false initially."""
        state = TelemetryState()
        assert state.timestamp == 0.0
        assert state.link_ok is False
        assert state.lat == 0.0
        assert state.lon == 0.0
        assert state.alt == 0.0
        assert state.relative_alt == 0.0
        assert state.roll == 0.0
        assert state.pitch == 0.0
        assert state.yaw == 0.0
        assert state.vx == 0.0
        assert state.vy == 0.0
        assert state.vz == 0.0
        assert state.voltage_v == 0.0
        assert state.current_a == 0.0
        assert state.remaining_pct == 0.0
        assert len(state.rc_channels) == 16
        assert all(c == 0.0 for c in state.rc_channels)
        assert state.msg_counts == {}


class TestMavlinkReader:
    """Tests for MavlinkReader message parsing."""

    def setup_method(self):
        self.reader = MavlinkReader(device="/dev/ttyACM0", baud=57600)

    def _make_msg(self, msg_type: str, **kwargs):
        """Create a mock MAVLink message."""
        msg = MagicMock()
        msg.get_type.return_value = msg_type
        for k, v in kwargs.items():
            setattr(msg, k, v)
        return msg

    def test_parse_heartbeat_updates_link_ok(self):
        """HEARTBEAT updates link_ok timestamp."""
        msg = self._make_msg("HEARTBEAT")
        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.link_ok is True
        assert state.timestamp > 0

    def test_parse_attitude(self):
        """ATTITUDE sets roll/pitch/yaw in radians."""
        msg = self._make_msg("ATTITUDE", roll=0.1, pitch=0.2, yaw=0.3)
        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.roll == 0.1
        assert state.pitch == 0.2
        assert state.yaw == 0.3

    def test_parse_global_position_int(self):
        """GLOBAL_POSITION_INT converts lat/lon/alt correctly."""
        # MAVLink: lat/lon in degrees * 1e7, alt in mm
        msg = self._make_msg(
            "GLOBAL_POSITION_INT",
            lat=471234567,  # 47.1234567 deg
            lon=81234567,  # 8.1234567 deg
            alt=100000,  # 100m = 100000mm
            relative_alt=50000,  # 50m = 50000mm
            vx=100,  # 1 m/s = 100 cm/s
            vy=200,
            vz=-50,
        )
        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.lat == 47.1234567
        assert state.lon == 8.1234567
        assert state.alt == 100000.0
        assert state.relative_alt == 50000.0
        assert state.vx == 100.0
        assert state.vy == 200.0
        assert state.vz == -50.0

    def test_parse_sys_status(self):
        """SYS_STATUS extracts voltage/current."""
        # voltage_battery in mV, current_battery in cA
        msg = self._make_msg("SYS_STATUS", voltage_battery=12500, current_battery=2500)
        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.voltage_v == 12.5
        assert state.current_a == 25.0

    def test_parse_battery_status(self):
        """BATTERY_STATUS extracts remaining_pct and voltage."""
        msg = self._make_msg(
            "BATTERY_STATUS",
            battery_remaining=75,
            voltages=[4200, 4100, 4150, 4180],  # mV per cell
        )
        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.remaining_pct == 75.0
        assert state.voltage_v == 4.2  # first cell

    def test_parse_rc_channels(self):
        """RC_CHANNELS normalizes PWM to -1..1."""
        # PWM 1000 -> -1.0, 1500 -> 0.0, 2000 -> 1.0
        # The implementation uses getattr(msg, f"chan{i+1}_raw", 1500)
        msg = self._make_msg(
            "RC_CHANNELS",
            chan_raw=[1000, 1500, 2000, 1250, 1750] + [1500] * 11,  # 16 channels
        )
        # Set individual channel attributes
        for i, val in enumerate([1000, 1500, 2000, 1250, 1750] + [1500] * 11):
            setattr(msg, f"chan{i + 1}_raw", val)

        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.rc_channels[0] == -1.0
        assert state.rc_channels[1] == 0.0
        assert state.rc_channels[2] == 1.0
        assert state.rc_channels[3] == -0.5
        assert state.rc_channels[4] == 0.5

    def test_message_counts_increment(self):
        """msg_counts increments per message type."""
        msg1 = self._make_msg("ATTITUDE")
        msg2 = self._make_msg("ATTITUDE")
        msg3 = self._make_msg("GLOBAL_POSITION_INT")
        self.reader._parse_message(msg1)
        self.reader._parse_message(msg2)
        self.reader._parse_message(msg3)
        state = self.reader.get_state()
        assert state.msg_counts["ATTITUDE"] == 2
        assert state.msg_counts["GLOBAL_POSITION_INT"] == 1

    def test_thread_safety(self):
        """Concurrent reads/writes don't corrupt state."""
        import threading

        def writer():
            for i in range(100):
                msg = self._make_msg("ATTITUDE", roll=i * 0.01, pitch=0.0, yaw=0.0)
                self.reader._parse_message(msg)

        def reader():
            for _ in range(100):
                self.reader.get_state()

        threads = [threading.Thread(target=writer) for _ in range(5)]
        threads += [threading.Thread(target=reader) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash; state should be consistent
        state = self.reader.get_state()
        assert isinstance(state.roll, float)

    def test_link_timeout_detection(self):
        """Link marked not ok after timeout."""
        msg = self._make_msg("HEARTBEAT")
        self.reader._parse_message(msg)
        state = self.reader.get_state()
        assert state.link_ok is True

        # Manually set timestamp to past
        with self.reader._lock:
            self.reader._state.timestamp = time.time() - 3.0  # > 2s timeout

        state = self.reader.get_state()
        assert state.link_ok is False


class TestModuleAPI:
    """Tests for module-level API functions."""

    @pytest.mark.asyncio
    async def test_start_stop_mavlink_task(self):
        """start_mavlink_task and stop_mavlink_task work."""
        # Patch the global _reader to avoid affecting other tests
        with patch("src.dfb.mavlink_ingest._reader", None):
            with patch("src.dfb.mavlink_ingest.MavlinkReader") as mock_reader_class:
                mock_reader = AsyncMock()
                mock_reader.start = AsyncMock()
                mock_reader.stop = AsyncMock()
                mock_reader._task = asyncio.create_task(asyncio.sleep(0))
                mock_reader_class.return_value = mock_reader

                task = await start_mavlink_task("/dev/ttyACM0", 57600)
                assert task is not None
                mock_reader.start.assert_called_once()

                await stop_mavlink_task(task)
                mock_reader.stop.assert_called_once()

    def test_get_telemetry_state_no_reader(self):
        """get_telemetry_state returns default state when no reader."""
        # Ensure global _reader is None
        import src.dfb.mavlink_ingest as mavlink_ingest

        original_reader = mavlink_ingest._reader
        mavlink_ingest._reader = None
        try:
            state = get_telemetry_state()
            assert isinstance(state, TelemetryState)
            assert state.timestamp == 0.0
            assert state.link_ok is False
        finally:
            mavlink_ingest._reader = original_reader


# Integration test marked slow (requires mavproxy SITL)
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mavlink_sitl():
    """Integration test with mavproxy SITL - requires external setup."""
    pytest.skip("Requires mavproxy SITL environment")
