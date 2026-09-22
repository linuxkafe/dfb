"""Tests for Fly Brain CLI."""
import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.dfb.cli import app
from src.dfb.client import (
    AdvisoryResponse,
    CommandResponse,
    DecideResponse,
    HealthResponse,
    MAVLinkTelemetryResponse,
    SafetyStatusResponse,
    SafetyViolationResponse,
    TelemetryDecideResponse,
    TelemetryResponse,
    TokenResponse,
    VerifyResponse,
    VersionResponse,
)

# Create mock response factories using dataclasses from client module
# These are JSON serializable via __dict__

# Create mock instances with default values
def MockHealthResponse():
    return HealthResponse(status="ok", version="0.1.0")
def MockVersionResponse():
    return VersionResponse(version="0.1.0")
def MockDecideResponse():
    return DecideResponse(action="UP", confidence=0.9, logits=[0.1, 0.2, 0.3, 0.4])
def MockAdvisoryResponse():
    return AdvisoryResponse(heading_deg=90.0, altitude_m=50.0, speed_mps=10.0, mode="GUIDED", reason="Navigating", distance_to_target=1000.0, bearing_to_target=90.0)
def MockSafetyViolationResponse():
    return SafetyViolationResponse(category="BATTERY", message="Low battery", severity="WARNING", value=15.0, limit=20.0)
def MockSafetyStatusResponse():
    return SafetyStatusResponse(safe=True, violations=[], warnings=[], battery_pct=80.0, link_ok=True, link_age_s=0.1, gps_fix_type=3, hdop=1.0, vdop=1.0, ground_speed=10.0, climb_rate=0.0, alt_agl=50.0)
def MockTelemetryDecideResponse():
    return TelemetryDecideResponse(advisory=MockAdvisoryResponse(), safety=MockSafetyStatusResponse())
def MockTokenResponse():
    return TokenResponse(token="abc12345", expires_in=30.0)
def MockCommandResponse():
    return CommandResponse(success=True, message="OK")
def MockVerifyResponse():
    return VerifyResponse(valid=True, expires_in=15.0)
def MockMAVLinkTelemetryResponse():
    return MAVLinkTelemetryResponse(timestamp=1234567890.0, link_ok=True, position={"lat": 47.0, "lon": 8.0, "alt": 100.0, "relative_alt": 50.0}, attitude={"roll": 0.1, "pitch": 0.0, "yaw": 1.57}, velocity={"vx": 10.0, "vy": 0.0, "vz": 0.0}, battery={"voltage_v": 12.0, "current_a": 5.0, "remaining_pct": 80.0}, rc_channels=[0.0]*16, message_counts={"HEARTBEAT": 10}, flight_mode="GUIDED", armed=True)
def MockTelemetryResponse():
    return TelemetryResponse(primary_source="mavlink", mavlink=MockMAVLinkTelemetryResponse())


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for CLI tests."""
        from src.dfb.client import HttpDeckClient

        # Create a mock class that inherits from HttpDeckClient
        class MockHttpDeckClient(HttpDeckClient):
            def __init__(self, *args, **kwargs):
                self._decide_result = MockDecideResponse()
                self._decide_telemetry_result = MockTelemetryDecideResponse()
                self._issue_token_result = MockTokenResponse()
                self._command_result = MockCommandResponse()
                self._verify_token_result = MockVerifyResponse()
                self._telemetry_result = MockTelemetryResponse()

            def health(self):
                return MockHealthResponse()

            def version(self):
                return MockVersionResponse()

            def decide(self, position, grid, exit):
                return self._decide_result

            def decide_telemetry(self, target_lat=None, target_lon=None, target_alt=None, target_speed=None):
                return self._decide_telemetry_result

            def issue_token(self):
                return self._issue_token_result

            def command(self, action, params=None, token=None):
                return self._command_result

            def verify_token(self, token):
                return self._verify_token_result

            def telemetry(self):
                return self._telemetry_result

        with patch("src.dfb.cli.HttpDeckClient", MockHttpDeckClient):
            client = MockHttpDeckClient("steamdeck", 8082)
            yield client

    @pytest.fixture
    def mock_grpc_client(self):
        """Mock gRPC client for CLI tests."""
        from src.dfb.client import GrpcDeckClient

        class MockGrpcDeckClient(GrpcDeckClient):
            def __init__(self, *args, **kwargs):
                self._decide_telemetry_result = MockTelemetryDecideResponse()
                self._issue_token_result = MockTokenResponse()
                self._command_result = MockCommandResponse()
                self._verify_token_result = MockVerifyResponse()
                self._telemetry_result = MockTelemetryResponse()

            async def health(self):
                return MockHealthResponse()

            async def version(self):
                return MockVersionResponse()

            async def decide_telemetry(self, target_lat=None, target_lon=None, target_alt=None, target_speed=None):
                return self._decide_telemetry_result

            async def issue_token(self):
                return self._issue_token_result

            async def command(self, action, params=None, token=None):
                return self._command_result

            async def verify_token(self, token):
                return self._verify_token_result

            async def telemetry(self):
                return self._telemetry_result

            async def close(self):
                pass

        with patch("src.dfb.cli.GrpcDeckClient", MockGrpcDeckClient):
            client = MockGrpcDeckClient("steamdeck", 8083)
            yield client

    def test_health_command(self, runner, mock_http_client):
        """Test dfb health command."""
        mock_http_client._health_result = MockHealthResponse()
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "ok" in result.stdout
        assert "0.1.0" in result.stdout

    def test_version_command(self, runner, mock_http_client):
        """Test dfb version command."""
        mock_http_client._version_result = MockVersionResponse()
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout

    def test_decide_maze_command(self, runner, mock_http_client):
        """Test dfb decide command (legacy maze mode)."""
        mock_http_client._decide_result = MockDecideResponse()
        state_json = json.dumps({
            "position": [0, 0],
            "grid": [[0]*10 for _ in range(10)],
            "exit": [9, 9]
        })
        result = runner.invoke(app, ["decide", state_json])
        assert result.exit_code == 0
        assert "UP" in result.stdout
        assert "0.9" in result.stdout

    def test_decide_invalid_json(self, runner, mock_http_client):
        """Test dfb decide with invalid JSON."""
        result = runner.invoke(app, ["decide", "not valid json"])
        assert result.exit_code == 1
        assert "Invalid JSON" in result.stderr

    def test_decide_telemetry_command(self, runner, mock_http_client):
        """Test dfb decide-telemetry command."""
        mock_http_client._decide_telemetry_result = MockTelemetryDecideResponse()
        result = runner.invoke(app, ["decide-telemetry", "--lat", "47.001", "--lon", "8.001"])
        assert result.exit_code == 0
        assert "90.0" in result.stdout
        assert "GUIDED" in result.stdout

    def test_issue_token_command(self, runner, mock_http_client):
        """Test dfb issue-token command."""
        mock_http_client._issue_token_result = MockTokenResponse()
        result = runner.invoke(app, ["issue-token"])
        assert result.exit_code == 0
        assert "abc12345" in result.stdout
        assert "30.0" in result.stdout

    def test_command_with_token(self, runner, mock_http_client):
        """Test dfb command with token."""
        mock_http_client._command_result = MockCommandResponse()
        result = runner.invoke(app, ["command", "ARM", "--token", "abc12345"])
        assert result.exit_code == 0
        assert "OK" in result.stdout
        assert "success" in result.stdout.lower()

    def test_command_with_params(self, runner, mock_http_client):
        """Test dfb command with params."""
        mock_http_client._command_result = MockCommandResponse()
        result = runner.invoke(app, ["command", "ARM", "--token", "abc12345", "--params", '{"force": true}'])
        assert result.exit_code == 0
        assert "OK" in result.stdout

    def test_verify_token_command(self, runner, mock_http_client):
        """Test dfb verify-token command."""
        mock_http_client._verify_token_result = MockVerifyResponse()
        result = runner.invoke(app, ["verify-token", "abc12345"])
        assert result.exit_code == 0
        assert "true" in result.stdout.lower()
        assert "15.0" in result.stdout

    def test_telemetry_command(self, runner, mock_http_client):
        """Test dfb telemetry command."""
        mock_http_client._telemetry_result = MockTelemetryResponse()
        result = runner.invoke(app, ["telemetry"])
        assert result.exit_code == 0
        assert "mavlink" in result.stdout

    def test_transport_option(self, runner, mock_http_client):
        """Test --transport option."""
        mock_http_client._decide_result = MockDecideResponse()
        state_json = json.dumps({
            "position": [0, 0],
            "grid": [[0]*10 for _ in range(10)],
            "exit": [9, 9]
        })
        result = runner.invoke(app, ["decide", state_json, "--transport", "http"])
        assert result.exit_code == 0

    def test_host_port_options(self, runner, mock_http_client):
        """Test --host and --port options."""
        mock_http_client._health_result = MockHealthResponse()
        result = runner.invoke(app, ["health", "--host", "custom", "--port", "9090"])
        assert result.exit_code == 0


class TestCLIEnvVars:
    """Tests for CLI environment variable handling."""

    def test_create_client_from_env(self):
        """Test create_client_from_env uses env vars."""
        with patch.dict("os.environ", {"DFB_HOST": "myhost", "DFB_PORT": "9090"}):
            from src.dfb.client import create_client_from_env
            client = create_client_from_env()
            assert client.base_url == "http://myhost:9090"

    def test_create_client_defaults(self):
        """Test create_client_from_env defaults."""
        with patch.dict("os.environ", {}, clear=True):
            from src.dfb.client import create_client_from_env
            client = create_client_from_env()
            assert client.base_url == "http://steamdeck:8082"
