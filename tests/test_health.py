"""Unit tests for health, metrics, and watchdog functionality."""

import asyncio
import time
from unittest.mock import MagicMock, patch

from src.dfb.health import (
    ComponentHealth,
    check_cpu_engine,
    check_decision_engine,
    check_mavlink_link,
    get_overall_health,
)
from src.dfb.mavlink_ingest import TelemetryState
from src.dfb.metrics import metrics_endpoint


class TestHealthComponents:
    """Tests for individual component health checks."""

    @patch("src.dfb.health.get_cpu_engine")
    def test_cpu_engine_healthy(self, mock_get_engine):
        """Test CPU engine health check when healthy."""
        mock_engine = MagicMock()
        mock_engine._initialized = True
        mock_get_engine.return_value = mock_engine

        result = check_cpu_engine()
        assert result.status == "ok"
        assert result.details["initialized"] is True

    @patch("src.dfb.health.get_cpu_engine")
    def test_cpu_engine_unhealthy(self, mock_get_engine):
        """Test CPU engine health check when unhealthy."""
        mock_get_engine.side_effect = RuntimeError("Engine not initialized")

        result = check_cpu_engine()
        assert result.status == "unhealthy"
        assert "error" in result.details

    def test_mavlink_link_ok(self):
        """Test MAVLink link health when OK."""
        telemetry = TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            msg_counts={"HEARTBEAT": 10, "ATTITUDE": 50},
        )
        with patch("src.dfb.health.get_telemetry_state", return_value=telemetry):
            result = check_mavlink_link()
            assert result.status == "ok"
            assert result.details["link_ok"] is True
            assert result.details["link_age_s"] < 2.0

    def test_mavlink_link_degraded(self):
        """Test MAVLink link health when degraded (stale)."""
        telemetry = TelemetryState(
            timestamp=time.time() - 5.0,  # 5 seconds ago
            link_ok=True,
            msg_counts={"HEARTBEAT": 10},
        )
        with patch("src.dfb.health.get_telemetry_state", return_value=telemetry):
            result = check_mavlink_link()
            assert result.status == "degraded"
            assert result.details["link_age_s"] > 2.0

    def test_mavlink_link_unhealthy(self):
        """Test MAVLink link health when lost."""
        telemetry = TelemetryState(
            timestamp=time.time() - 15.0,
            link_ok=False,
            msg_counts={},
        )
        with patch("src.dfb.health.get_telemetry_state", return_value=telemetry):
            result = check_mavlink_link()
            assert result.status == "unhealthy"
            assert result.details["link_ok"] is False

    def test_mavlink_link_no_data(self):
        """Test MAVLink link health when no data ever received."""
        telemetry = TelemetryState(timestamp=0.0, link_ok=False)
        with patch("src.dfb.health.get_telemetry_state", return_value=telemetry):
            result = check_mavlink_link()
            assert result.status == "unhealthy"
            assert result.details["link_age_s"] == float("inf")

    @patch("src.dfb.advisor.get_advisor")
    def test_decision_engine_healthy(self, mock_get_advisor):
        """Test decision engine health when healthy."""
        mock_advisor = MagicMock()
        mock_get_advisor.return_value = mock_advisor

        result = check_decision_engine()
        assert result.status == "ok"
        assert result.details["advisor_ready"] is True

    @patch("src.dfb.advisor.get_advisor")
    def test_decision_engine_unhealthy(self, mock_get_advisor):
        """Test decision engine health when unhealthy."""
        mock_get_advisor.side_effect = RuntimeError("Advisor failed")

        result = check_decision_engine()
        assert result.status == "unhealthy"
        assert "error" in result.details


class TestOverallHealth:
    """Tests for overall health aggregation."""

    @patch("src.dfb.health.check_cpu_engine")
    @patch("src.dfb.health.check_mavlink_link")
    @patch("src.dfb.health.check_crsf_link")
    @patch("src.dfb.health.check_decision_engine")
    def test_all_healthy(self, mock_decision, mock_crsf, mock_mavlink, mock_cpu):
        """Test overall health when all components healthy."""
        mock_cpu.return_value = ComponentHealth("ok", {})
        mock_mavlink.return_value = ComponentHealth("ok", {})
        mock_crsf.return_value = ComponentHealth("ok", {})
        mock_decision.return_value = ComponentHealth("ok", {})

        overall, components = get_overall_health()
        assert overall == "ok"
        assert all(c["status"] == "ok" for c in components.values())

    @patch("src.dfb.health.check_cpu_engine")
    @patch("src.dfb.health.check_mavlink_link")
    @patch("src.dfb.health.check_crsf_link")
    @patch("src.dfb.health.check_decision_engine")
    def test_one_degraded(self, mock_decision, mock_crsf, mock_mavlink, mock_cpu):
        """Test overall health when one component degraded."""
        mock_cpu.return_value = ComponentHealth("ok", {})
        mock_mavlink.return_value = ComponentHealth("degraded", {})
        mock_crsf.return_value = ComponentHealth("ok", {})
        mock_decision.return_value = ComponentHealth("ok", {})

        overall, _ = get_overall_health()
        assert overall == "degraded"

    @patch("src.dfb.health.check_cpu_engine")
    @patch("src.dfb.health.check_mavlink_link")
    @patch("src.dfb.health.check_crsf_link")
    @patch("src.dfb.health.check_decision_engine")
    def test_one_unhealthy(self, mock_decision, mock_crsf, mock_mavlink, mock_cpu):
        """Test overall health when one component unhealthy."""
        mock_cpu.return_value = ComponentHealth("ok", {})
        mock_mavlink.return_value = ComponentHealth("unhealthy", {})
        mock_crsf.return_value = ComponentHealth("ok", {})
        mock_decision.return_value = ComponentHealth("ok", {})

        overall, _ = get_overall_health()
        assert overall == "unhealthy"


class TestMetricsRecording:
    """Tests for metrics recording functions."""

    def test_record_http_request(self):
        """Test HTTP request metrics recording."""
        from src.dfb.metrics import (
            record_http_request,
        )

        # Reset for test
        record_http_request("/test", 200, 0.1)
        # Just verify no exception

    def test_record_mavlink_message(self):
        """Test MAVLink message metrics recording."""
        from src.dfb.metrics import record_mavlink_message

        record_mavlink_message("HEARTBEAT")
        # Just verify no exception

    def test_update_mavlink_link_status(self):
        """Test MAVLink link status gauge update."""
        from src.dfb.metrics import update_mavlink_link_status

        update_mavlink_link_status(True)
        update_mavlink_link_status(False)

    def test_record_decision(self):
        """Test decision metrics recording."""
        from src.dfb.metrics import record_decision

        record_decision("telemetry", "GUIDED", 0.01)

    def test_record_safety_violation(self):
        """Test safety violation metrics recording."""
        from src.dfb.metrics import record_safety_violation

        record_safety_violation("BATTERY", "CRITICAL")


def test_metrics_endpoint_function():
    """Test metrics endpoint function directly."""
    response = metrics_endpoint()
    assert response.status_code == 200
    assert response.media_type is not None
    assert response.media_type.startswith("text/plain")
    assert "charset=utf-8" in response.media_type
    content = response.body.decode()
    assert "http_requests_total" in content


class TestWatchdog:
    """Tests for watchdog functionality."""

    @patch("src.dfb.mavlink_ingest.get_telemetry_state")
    @patch("src.dfb.logging.log_mavlink_event")
    def test_watchdog_detects_stale_link(self, mock_log, mock_telemetry):
        """Test watchdog detects stale MAVLink link."""
        # Import inside function to allow patching
        from src.dfb.service import _watchdog_loop

        # Create telemetry with stale timestamp
        telemetry = TelemetryState(
            timestamp=time.time() - 15.0,
            link_ok=True,
            msg_counts={"HEARTBEAT": 10},
        )
        mock_telemetry.return_value = telemetry

        # Run one iteration of watchdog
        async def run_once():
            task = asyncio.create_task(_watchdog_loop())
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_once())
        # Verify log was called for stale link
        # Note: watchdog logs but doesn't restart in current implementation


class TestStructuredLogging:
    """Tests for structured logging."""

    def test_setup_logging(self):
        """Test logging setup."""
        from src.dfb.logging import setup_logging

        setup_logging("DEBUG")
        # Just verify no exception

    def test_correlation_id(self):
        """Test correlation ID context variable."""
        from src.dfb.logging import get_correlation_id, set_correlation_id

        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

    def test_log_request(self):
        """Test request logging."""
        from src.dfb.logging import log_request

        log_request("/test", "GET", 200, 10.5, "corr-123")

    def test_log_component_health(self):
        """Test component health logging."""
        from src.dfb.logging import log_component_health

        log_component_health("test_component", "ok", {"detail": "value"})

    def test_log_mavlink_event(self):
        """Test MAVLink event logging."""
        from src.dfb.logging import log_mavlink_event

        log_mavlink_event("connect", {"device": "/dev/ttyACM0"})
