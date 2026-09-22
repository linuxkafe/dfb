"""Additional tests for client.py gRPC paths and uncovered code."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.dfb.client import (
    GrpcDeckClient,
    HttpDeckClient,
    create_client_from_env,
)
from src.dfb.client import (
    HealthResponse, VersionResponse, DecideResponse,
    AdvisoryResponse, SafetyViolationResponse, SafetyStatusResponse,
    TelemetryDecideResponse, TokenResponse, CommandResponse, VerifyResponse,
    MAVLinkTelemetryResponse, TelemetryResponse, CRSFTelemetryResponse,
)


class TestGrpcDeckClient:
    """Tests for GrpcDeckClient."""

    @pytest.fixture
    def grpc_client(self):
        return GrpcDeckClient(host="steamdeck", port=8083)

    @pytest.mark.asyncio
    async def test_grpc_client_connect_close(self, grpc_client):
        """Test gRPC client connection and close."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub.return_value = MagicMock()

            stub = await grpc_client._get_stub()
            assert stub is not None

            await grpc_client.close()
            mock_ch.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_grpc_health(self, grpc_client):
        """Test gRPC health method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.GetHealth = AsyncMock(return_value=MagicMock(status="ok", version="0.1.0"))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.health()
            assert isinstance(result, HealthResponse)
            assert result.status == "ok"
            assert result.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_grpc_version(self, grpc_client):
        """Test gRPC version method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.GetVersion = AsyncMock(return_value=MagicMock(version="0.1.0"))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.version()
            assert isinstance(result, VersionResponse)
            assert result.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_grpc_telemetry(self, grpc_client):
        """Test gRPC telemetry method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.GetTelemetry = AsyncMock(return_value=MagicMock(
                link_ok=True, source="mavlink",
                mavlink=MagicMock(link_ok=True, flight_mode="GUIDED"),
                crsf=MagicMock(link_ok=False),
                fused=MagicMock(rc_channels=[0.0]*16)
            ))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.telemetry()
            assert isinstance(result, TelemetryResponse)
            assert result.primary_source == "mavlink"

    @pytest.mark.asyncio
    async def test_grpc_decide_telemetry(self, grpc_client):
        """Test gRPC decide_telemetry method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.Decide = AsyncMock(return_value=MagicMock(
                advisory=MagicMock(
                    heading_deg=90.0, altitude_m=50.0, speed_mps=10.0,
                    mode="GUIDED", reason="Navigating",
                    distance_to_target=1000.0, bearing_to_target=90.0
                ),
                safety=MagicMock(
                    safe=True, violations=[], warnings=[],
                    battery_pct=80.0, link_ok=True, link_age_s=0.1,
                    gps_fix_type=3, hdop=1.0, vdop=1.0,
                    ground_speed=10.0, climb_rate=0.0, alt_agl=50.0
                )
            ))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.decide_telemetry(
                target_lat=47.001, target_lon=8.001
            )
            assert isinstance(result, TelemetryDecideResponse)
            assert result.advisory is not None
            assert result.advisory.mode == "GUIDED"

    @pytest.mark.asyncio
    async def test_grpc_issue_token(self, grpc_client):
        """Test gRPC issue_token method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.IssueToken = AsyncMock(return_value=MagicMock(token="abc12345", expires_in=30.0))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.issue_token()
            assert isinstance(result, TokenResponse)
            assert result.token == "abc12345"

    @pytest.mark.asyncio
    async def test_grpc_command(self, grpc_client):
        """Test gRPC command method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.SendCommand = AsyncMock(return_value=MagicMock(success=True, message="OK"))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.command(action="ARM", token="abc12345")
            assert isinstance(result, CommandResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_grpc_verify_token(self, grpc_client):
        """Test gRPC verify_token method."""
        with patch("grpc.aio.insecure_channel") as mock_channel, \
             patch("src.dfb.grpc.flybrain_pb2_grpc.FlyBrainServiceStub") as mock_stub_class:
            mock_ch = AsyncMock()
            mock_channel.return_value = mock_ch
            mock_stub = AsyncMock()
            mock_stub.VerifyToken = AsyncMock(return_value=MagicMock(valid=True, expires_in=15.0))
            mock_stub_class.return_value = mock_stub

            result = await grpc_client.verify_token(token="abc12345")
            assert isinstance(result, VerifyResponse)
            assert result.valid is True


class TestHttpDeckClientAdditional:
    """Additional tests for HttpDeckClient."""

    @pytest.fixture
    def mock_session(self):
        from unittest.mock import Mock
        return Mock()

    def test_http_decide_telemetry(self, mock_session):
        """Test HTTP decide_telemetry."""
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "advisory": {
                "heading_deg": 90.0, "altitude_m": 50.0, "speed_mps": 10.0,
                "mode": "GUIDED", "reason": "Navigating",
                "distance_to_target": 1000.0, "bearing_to_target": 90.0
            },
            "safety": {
                "safe": True, "violations": [], "warnings": [],
                "battery_pct": 80.0, "link_ok": True, "link_age_s": 0.1,
                "gps_fix_type": 3, "hdop": 1.0, "vdop": 1.0,
                "ground_speed": 10.0, "climb_rate": 0.0, "alt_agl": 50.0
            }
        }
        mock_resp.raise_for_status.return_value = None
        mock_session.post.return_value = mock_resp

        client = HttpDeckClient(session=mock_session)
        result = client.decide_telemetry(target_lat=47.001, target_lon=8.001)
        assert result.advisory is not None
        assert result.advisory.mode == "GUIDED"

    def test_http_command_with_token(self, mock_session):
        """Test HTTP command with token."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"success": True, "message": "OK"}
        mock_resp.raise_for_status.return_value = None
        mock_session.post.return_value = mock_resp

        client = HttpDeckClient(session=mock_session)
        result = client.command(action="ARM", token="abc12345")
        assert result.success is True
        called_headers = mock_session.post.call_args.kwargs.get("headers", {})
        assert called_headers.get("X-Confirmation-Token") == "abc12345"

    def test_http_verify_token(self, mock_session):
        """Test HTTP verify_token."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"valid": True, "expires_in": 15.0}
        mock_resp.raise_for_status.return_value = None
        mock_session.get.return_value = mock_resp

        client = HttpDeckClient(session=mock_session)
        result = client.verify_token(token="abc12345")
        assert result.valid is True

    def test_http_telemetry_with_crsf(self, mock_session):
        """Test HTTP telemetry with CRSF data."""
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "primary_source": "crsf",
            "mavlink": {
                "timestamp": 1234567890.0, "link_ok": False,
                "position": {"lat": 0.0, "lon": 0.0, "alt": 0.0, "relative_alt": 0.0},
                "attitude": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                "velocity": {"vx": 0.0, "vy": 0.0, "vz": 0.0},
                "battery": {"voltage_v": 0.0, "current_a": 0.0, "remaining_pct": 0.0},
                "rc_channels": [0.0]*16, "message_counts": {},
                "flight_mode": "UNKNOWN", "armed": False
            },
            "crsf": {
                "timestamp": 1234567890.0, "link_ok": True,
                "rc_channels": [0.0]*16, "rssi": -50, "lq": 90, "snr": 10,
                "rf_mode": 0, "voltage": 12.0, "current": 5.0,
                "capacity": 1000, "gps": None, "message_counts": {}
            },
            "fused": {"rc_channels": [0.0]*16, "timestamp": 1234567890.0}
        }
        mock_resp.raise_for_status.return_value = None
        mock_session.get.return_value = mock_resp

        client = HttpDeckClient(session=mock_session)
        result = client.telemetry()
        assert result.primary_source == "crsf"
        assert result.crsf is not None
        assert result.crsf.rssi == -50


class TestCreateClientFromEnv:
    """Tests for create_client_from_env."""

    def test_create_client_from_env_custom(self):
        """Test with custom env vars."""
        import os
        with patch.dict(os.environ, {"DFB_HOST": "myhost", "DFB_PORT": "9090"}):
            client = create_client_from_env()
            assert client.base_url == "http://myhost:9090"

    def test_create_client_from_env_defaults(self):
        """Test with default env vars."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            client = create_client_from_env()
            assert client.base_url == "http://steamdeck:8082"


class TestClientResponseSerialization:
    """Tests for response object serialization."""

    def test_telemetry_response_dict(self):
        """Test TelemetryResponse __dict__."""
        resp = TelemetryResponse(
            primary_source="mavlink",
            mavlink=MAVLinkTelemetryResponse(
                timestamp=1234567890.0, link_ok=True,
                position={}, attitude={}, velocity={}, battery={},
                rc_channels=[], message_counts={}, flight_mode="GUIDED", armed=True
            )
        )
        d = resp.__dict__
        assert d["primary_source"] == "mavlink"
        assert d["mavlink"].flight_mode == "GUIDED"

    def test_crsf_telemetry_response_dict(self):
        """Test CRSFTelemetryResponse __dict__."""
        resp = CRSFTelemetryResponse(
            timestamp=1234567890.0, link_ok=True,
            rc_channels=[0.0]*16, rssi=-50, lq=90, snr=10
        )
        d = resp.__dict__
        assert d["rssi"] == -50
        assert d["lq"] == 90

    def test_advisory_response_dict(self):
        """Test AdvisoryResponse __dict__."""
        resp = AdvisoryResponse(
            heading_deg=90.0, altitude_m=50.0, speed_mps=10.0,
            mode="GUIDED", reason="Test"
        )
        d = resp.__dict__
        assert d["heading_deg"] == 90.0
        assert d["mode"] == "GUIDED"

    def test_safety_status_response_dict(self):
        """Test SafetyStatusResponse __dict__."""
        resp = SafetyStatusResponse(
            safe=True, violations=[], warnings=[],
            battery_pct=80.0, link_ok=True, link_age_s=0.1,
            gps_fix_type=3, hdop=1.0, vdop=1.0,
            ground_speed=10.0, climb_rate=0.0, alt_agl=50.0
        )
        d = resp.__dict__
        assert d["safe"] is True
        assert d["battery_pct"] == 80.0