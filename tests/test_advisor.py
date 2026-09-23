"""Unit tests for advisor, safety envelope, and state estimator."""

import time

from src.dfb.advisor import (
    Advisor,
    MissionGoal,
    _is_auto_safety_mode,
    _is_manual_mode,
    _mode_allows_advisory,
)
from src.dfb.mavlink_ingest import TelemetryState
from src.dfb.safety_envelope import (
    DEFAULT_SAFETY_CONFIG,
    SafetyConfig,
    check_safety,
)
from src.dfb.state_estimator import (
    EstimatedState,
    bearing_to,
    distance_to,
    estimate_state,
)


class TestStateEstimator:
    """Tests for state estimation functions."""

    def test_bearing_to(self):
        """Test bearing calculation."""
        # Same point -> 0 bearing
        b = bearing_to(47.0, 8.0, 47.0, 8.0)
        assert b == 0.0

        # North
        b = bearing_to(48.0, 8.0, 47.0, 8.0)
        assert abs(b - 0.0) < 1.0

        # East
        b = bearing_to(47.0, 9.0, 47.0, 8.0)
        assert abs(b - 90.0) < 1.0

        # South
        b = bearing_to(46.0, 8.0, 47.0, 8.0)
        assert abs(b - 180.0) < 1.0

        # West
        b = bearing_to(47.0, 7.0, 47.0, 8.0)
        assert abs(b - 270.0) < 1.0

    def test_distance_to(self):
        """Test distance calculation."""
        # Same point -> 0 distance
        d = distance_to(47.0, 8.0, 47.0, 8.0)
        assert d == 0.0

        # ~111km per degree latitude
        d = distance_to(48.0, 8.0, 47.0, 8.0)
        assert abs(d - 111111.0) < 1000.0

    def test_estimate_state_valid(self):
        """Test state estimation with valid telemetry."""
        telemetry = TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.123456,
            lon=8.123456,
            alt=500000,  # 500m MSL
            relative_alt=100000,  # 100m AGL
            roll=0.1,
            pitch=0.05,
            yaw=1.57,  # ~90 deg (East)
            vx=1000,  # 10 m/s North
            vy=0,
            vz=0,
            remaining_pct=80.0,
            flight_mode="GUIDED",
            armed=True,
        )

        state = estimate_state(telemetry, home_position=(47.123456, 8.123456))

        assert state.valid is True
        assert state.up == 100.0  # 100m AGL
        assert abs(state.yaw - 1.57) < 0.01
        assert state.vn == 10.0  # 10 m/s North
        assert state.flight_mode == "UNKNOWN"  # Set by caller

    def test_estimate_state_no_link(self):
        """Test state estimation with no link."""
        telemetry = TelemetryState(
            timestamp=0.0,
            link_ok=False,
        )

        state = estimate_state(telemetry)
        assert state.valid is False
        assert state.flight_mode == "NO_LINK"


class TestSafetyEnvelope:
    """Tests for safety envelope checks."""

    def setup_method(self):
        self.config = SafetyConfig(
            min_lat=47.0,
            max_lat=48.0,
            min_lon=8.0,
            max_lon=9.0,
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

    def _make_state(self, **overrides) -> EstimatedState:
        """Create a valid EstimatedState with optional overrides."""
        raw = TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.5,
            lon=8.5,
            alt=500000,
            relative_alt=50000,  # 50m AGL
            roll=0.0,
            pitch=0.0,
            yaw=0.0,
            vx=0,
            vy=0,
            vz=0,
            remaining_pct=80.0,
        )
        state = estimate_state(raw, home_position=(47.5, 8.5))
        state.flight_mode = "GUIDED"
        state.armed = True
        state.gps_fix_type = 3
        state.hdop = 1.0
        state.vdop = 1.0
        for k, v in overrides.items():
            setattr(state, k, v)
        return state

    def test_safety_pass(self):
        """Test all safety checks pass."""
        state = self._make_state()
        status = check_safety(state, self.config)
        assert status.safe is True
        assert len(status.violations) == 0

    def test_geofence_violation_lat(self):
        """Test geofence latitude violation."""
        state = self._make_state()
        state._raw.lat = 46.0  # Outside min_lat
        status = check_safety(state, self.config)
        assert status.safe is False
        assert any(v.category == "GEOFENCE" for v in status.violations)

    def test_geofence_violation_lon(self):
        """Test geofence longitude violation."""
        state = self._make_state()
        state._raw.lon = 10.0  # Outside max_lon
        status = check_safety(state, self.config)
        assert status.safe is False
        assert any(v.category == "GEOFENCE" for v in status.violations)

    def test_altitude_floor(self):
        """Test minimum altitude violation."""
        state = self._make_state()
        state._raw.relative_alt = 5000  # 5m AGL
        state.up = 5.0
        status = check_safety(state, self.config)
        assert status.safe is False
        violations = [
            v
            for v in status.violations
            if v.category == "ALTITUDE" and v.severity == "CRITICAL"
        ]
        assert len(violations) > 0

    def test_altitude_ceiling(self):
        """Test maximum altitude violation."""
        state = self._make_state()
        state._raw.relative_alt = 150000  # 150m AGL
        state.up = 150.0
        status = check_safety(state, self.config)
        assert status.safe is False
        violations = [
            v
            for v in status.violations
            if v.category == "ALTITUDE" and v.severity == "CRITICAL"
        ]
        assert len(violations) > 0

    def test_battery_reserve(self):
        """Test battery reserve violation."""
        state = self._make_state()
        state._raw.remaining_pct = 10.0
        status = check_safety(state, self.config)
        assert status.safe is False
        assert any(v.category == "BATTERY" for v in status.violations)

    def test_link_loss(self):
        """Test link loss violation."""
        state = self._make_state()
        state._raw.link_ok = False
        state.timestamp = time.time() - 5.0  # 5 seconds ago
        status = check_safety(state, self.config)
        assert status.safe is False
        assert any(v.category == "LINK" for v in status.violations)

    def test_gps_fix_type(self):
        """Test GPS fix type violation."""
        state = self._make_state()
        state.gps_fix_type = 1  # No fix
        status = check_safety(state, self.config)
        assert status.safe is False
        assert any(v.category == "GPS" for v in status.violations)

    def test_speed_limit(self):
        """Test ground speed limit violation (WARNING level)."""
        state = self._make_state()
        state.ve = 25.0  # 25 m/s
        state.vn = 0.0
        status = check_safety(state, self.config)
        # Speed limit is WARNING, not CRITICAL - safe remains True
        assert status.safe is True
        assert any(v.category == "SPEED" for v in status.warnings)

    def test_climb_rate(self):
        """Test climb rate violation (WARNING level)."""
        state = self._make_state()
        state.vu = 10.0  # 10 m/s climb
        status = check_safety(state, self.config)
        assert status.safe is True
        msgs = [v.message for v in status.warnings if v.category == "SPEED"]
        assert any("Climb" in m for m in msgs)

    def test_sink_rate(self):
        """Test sink rate violation (WARNING level)."""
        state = self._make_state()
        state.vu = -5.0  # 5 m/s sink
        status = check_safety(state, self.config)
        assert status.safe is True
        msgs = [v.message for v in status.warnings if v.category == "SPEED"]
        assert any("Sink" in m for m in msgs)

    def test_attitude_limits(self):
        """Test roll/pitch limits (WARNING level)."""
        state = self._make_state()
        state.roll = 1.0  # ~57 deg
        state.pitch = 1.0
        status = check_safety(state, self.config)
        assert status.safe is True
        assert any(v.category == "ATTITUDE" for v in status.warnings)


class TestAdvisor:
    """Tests for advisory decision logic."""

    def setup_method(self):
        self.config = DEFAULT_SAFETY_CONFIG
        self.advisor = Advisor(self.config)

    def _make_safe_state(self, flight_mode: str = "GUIDED") -> EstimatedState:
        """Create a safe state for testing."""
        raw = TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.5,
            lon=8.5,
            alt=500000,
            relative_alt=50000,  # 50m AGL
            roll=0.0,
            pitch=0.0,
            yaw=0.0,
            vx=0,
            vy=0,
            vz=0,
            remaining_pct=80.0,
            flight_mode=flight_mode,
            armed=True,
        )
        state = estimate_state(raw, home_position=(47.5, 8.5))
        state.flight_mode = flight_mode
        state.armed = True
        state.gps_fix_type = 3
        state.hdop = 1.0
        state.vdop = 1.0
        return state

    def test_mode_allows_advisory(self):
        """Test mode compatibility checks."""
        assert _mode_allows_advisory("GUIDED") is True
        assert _mode_allows_advisory("AUTO") is True
        assert _mode_allows_advisory("LOITER") is True
        assert _mode_allows_advisory("MANUAL") is False
        assert _mode_allows_advisory("ACRO") is False

    def test_is_manual_mode(self):
        """Test manual mode detection."""
        assert _is_manual_mode("MANUAL") is True
        assert _is_manual_mode("ACRO") is True
        assert _is_manual_mode("STABILIZE") is True
        assert _is_manual_mode("GUIDED") is False

    def test_is_auto_safety_mode(self):
        """Test auto safety mode detection."""
        assert _is_auto_safety_mode("RTL") is True
        assert _is_auto_safety_mode("LAND") is True
        assert _is_auto_safety_mode("AUTO_RTL") is True
        assert _is_auto_safety_mode("GUIDED") is False

    def test_advisor_safety_violation_rtl(self):
        """Test advisor forces RTL on safety violation."""
        state = self._make_safe_state()
        state._raw.remaining_pct = 10.0  # Below reserve

        advisory = self.advisor.advise(state)

        assert advisory.mode == "RTL"
        assert "Safety violation" in advisory.reason

    def test_advisor_manual_mode_advisory_only(self):
        """Test advisor in manual mode returns advisory only."""
        state = self._make_safe_state("MANUAL")

        advisory = self.advisor.advise(state)

        assert advisory.mode == "ADVISORY"
        assert "pilot in control" in advisory.reason

    def test_advisor_auto_safety_mode(self):
        """Test advisor doesn't interfere with auto safety modes."""
        state = self._make_safe_state("RTL")

        advisory = self.advisor.advise(state)

        assert advisory.mode == "RTL"
        assert "automatic safety mode" in advisory.reason

    def test_advisor_waypoint_navigation(self):
        """Test advisor computes waypoint navigation."""
        state = self._make_safe_state("GUIDED")
        goal = MissionGoal(
            target_lat=47.501, target_lon=8.501, target_alt=60.0, target_speed=15.0
        )

        advisory = self.advisor.advise(state, goal)

        assert advisory.mode == "GUIDED"
        assert advisory.altitude_m == 60.0
        assert advisory.speed_mps == 15.0
        assert advisory.heading_deg >= 0.0
        assert advisory.heading_deg <= 360.0

    def test_advisor_loiter_at_target(self):
        """Test advisor loiters when at target."""
        state = self._make_safe_state("GUIDED")
        goal = MissionGoal(
            target_lat=47.5, target_lon=8.5, target_alt=50.0, loiter_radius=100.0
        )

        advisory = self.advisor.advise(state, goal)

        assert advisory.speed_mps == 0.0
        assert "loitering" in advisory.reason.lower()

    def test_advisor_unknown_mode(self):
        """Test advisor with unknown mode."""
        state = self._make_safe_state("UNKNOWN_MODE")

        advisory = self.advisor.advise(state)

        assert advisory.mode == "UNKNOWN_MODE"
        assert "not compatible" in advisory.reason


class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_full_pipeline_safe(self):
        """Test full pipeline with safe state."""
        raw = TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.5,
            lon=8.5,
            alt=500000,
            relative_alt=50000,
            roll=0.0,
            pitch=0.0,
            yaw=0.0,
            vx=0,
            vy=0,
            vz=0,
            remaining_pct=80.0,
            flight_mode="GUIDED",
            armed=True,
        )

        state = estimate_state(raw, home_position=(47.5, 8.5))
        state.flight_mode = "GUIDED"
        state.armed = True
        state.gps_fix_type = 3
        state.hdop = 1.0
        state.vdop = 1.0

        advisor = Advisor(DEFAULT_SAFETY_CONFIG)
        advisory = advisor.advise(
            state, MissionGoal(target_lat=47.501, target_lon=8.501)
        )

        assert advisory.mode == "GUIDED"
        assert advisory.safety is not None
        assert advisory.safety.safe is True

    def test_full_pipeline_battery_rtl(self):
        """Test full pipeline triggers RTL on low battery."""
        raw = TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.5,
            lon=8.5,
            alt=500000,
            relative_alt=50000,
            roll=0.0,
            pitch=0.0,
            yaw=0.0,
            vx=0,
            vy=0,
            vz=0,
            remaining_pct=10.0,  # Low battery
            flight_mode="GUIDED",
            armed=True,
        )

        state = estimate_state(raw, home_position=(47.5, 8.5))
        state.flight_mode = "GUIDED"
        state.armed = True
        state.gps_fix_type = 3
        state.hdop = 1.0
        state.vdop = 1.0

        advisor = Advisor(DEFAULT_SAFETY_CONFIG)
        advisory = advisor.advise(state)

        assert advisory.mode == "RTL"
        assert advisory.safety.safe is False
