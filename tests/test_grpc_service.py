"""Tests for Fly Brain gRPC service."""

import time
from unittest.mock import MagicMock, patch

import pytest

# For secure server test
try:
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from src.dfb.advisor import Advisory, SafetyStatus
from src.dfb.crsf_ingest import CRSFTelemetry

# Import generated gRPC code
from src.dfb.grpc import flybrain_pb2
from src.dfb.grpc_service import FlyBrainServicer
from src.dfb.mavlink_ingest import TelemetryState
from src.dfb.safety_envelope import SafetyViolation


class TestFlyBrainServicer:
    """Tests for FlyBrainServicer gRPC methods."""

    @pytest.fixture
    def servicer(self):
        return FlyBrainServicer()

    @pytest.fixture
    def mock_mavlink_telemetry(self):
        """Create mock MAVLink telemetry."""
        return TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.0,
            lon=8.0,
            alt=100000,
            relative_alt=50000,
            roll=0.1,
            pitch=0.0,
            yaw=1.57,
            vx=100,
            vy=0,
            vz=0,
            voltage_v=12.0,
            current_a=5.0,
            remaining_pct=80.0,
            rc_channels=[0.0] * 16,
            msg_counts={"HEARTBEAT": 10},
            flight_mode="GUIDED",
            armed=True,
            autopilot=3,
        )

    @pytest.fixture
    def mock_crsf_telemetry(self):
        """Create mock CRSF telemetry."""
        return CRSFTelemetry(
            timestamp=time.time(),
            link_ok=True,
            channels=[0.0] * 16,
            rssi=-50,
            lq=90,
            snr=10,
            rf_mode=0,
            voltage=12.0,
            current=5.0,
            capacity=1000,
            gps=None,
            msg_counts={},
        )

    @pytest.mark.asyncio
    async def test_get_health(self, servicer):
        """Test GetHealth RPC."""
        with patch("src.dfb.grpc_service.get_overall_health") as mock_health:
            mock_health.return_value = (
                "ok",
                {"cpu_engine": {"status": "ok", "details": {}}},
            )
            request = flybrain_pb2.HealthRequest()
            context = MagicMock()
            response = await servicer.GetHealth(request, context)
            assert response.status == "ok"
            assert response.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_get_version(self, servicer):
        """Test GetVersion RPC."""
        request = flybrain_pb2.VersionRequest()
        context = MagicMock()
        response = await servicer.GetVersion(request, context)
        assert response.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_get_telemetry(
        self, servicer, mock_mavlink_telemetry, mock_crsf_telemetry
    ):
        """Test GetTelemetry RPC."""
        with (
            patch(
                "src.dfb.grpc_service.get_telemetry_state",
                return_value=mock_mavlink_telemetry,
            ),
            patch(
                "src.dfb.grpc_service.get_crsf_state", return_value=mock_crsf_telemetry
            ),
        ):
            request = flybrain_pb2.TelemetryRequest()
            context = MagicMock()
            response = await servicer.GetTelemetry(request, context)
            assert response.link_ok is True
            assert response.source == "mavlink"
            assert response.mavlink is not None
            assert response.crsf is not None
            assert response.mavlink.flight_mode == "GUIDED"

    @pytest.mark.asyncio
    async def test_get_telemetry_stream(
        self, servicer, mock_mavlink_telemetry, mock_crsf_telemetry
    ):
        """Test GetTelemetryStream RPC."""
        with (
            patch(
                "src.dfb.grpc_service.get_telemetry_state",
                return_value=mock_mavlink_telemetry,
            ),
            patch(
                "src.dfb.grpc_service.get_crsf_state", return_value=mock_crsf_telemetry
            ),
        ):
            request = flybrain_pb2.TelemetryStreamRequest(interval_ms=100)
            context = MagicMock()
            context.is_active.return_value = True

            # Get first response
            async_gen = servicer.GetTelemetryStream(request, context)
            response = await async_gen.__anext__()
            assert response.link_ok is True
            assert response.source == "mavlink"

    @pytest.mark.asyncio
    async def test_decide_telemetry_mode(self, servicer, mock_mavlink_telemetry):
        """Test Decide RPC in telemetry mode."""
        with (
            patch(
                "src.dfb.grpc_service.get_telemetry_state",
                return_value=mock_mavlink_telemetry,
            ),
            patch("src.dfb.grpc_service.get_crsf_state") as mock_crsf,
            patch("src.dfb.grpc_service.estimate_state") as mock_estimate,
            patch("src.dfb.grpc_service.check_safety") as mock_safety,
            patch("src.dfb.grpc_service.get_advisor") as mock_get_advisor,
        ):
            mock_crsf.return_value = MagicMock(link_ok=False)
            mock_state = MagicMock(
                valid=True,
                up=50.0,
                ve=10.0,
                vn=0.0,
                vu=0.0,
                yaw=1.57,
                roll=0.0,
                pitch=0.0,
                flight_mode="GUIDED",
                armed=True,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                _raw=mock_mavlink_telemetry,
            )
            mock_estimate.return_value = mock_state
            mock_safety.return_value = SafetyStatus(
                safe=True,
                violations=[],
                warnings=[],
                battery_pct=80.0,
                link_ok=True,
                link_age_s=0.1,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                ground_speed=10.0,
                climb_rate=0.0,
                alt_agl=50.0,
            )
            mock_advisor = MagicMock()
            mock_advisor.advise.return_value = Advisory(
                heading_deg=90.0,
                altitude_m=50.0,
                speed_mps=10.0,
                mode="GUIDED",
                reason="Navigating to target",
                distance_to_target=1000.0,
                bearing_to_target=90.0,
                safety=mock_safety.return_value,
            )
            mock_get_advisor.return_value = mock_advisor

            request = flybrain_pb2.DecideRequest(
                use_telemetry=True,
                target_lat=47.001,
                target_lon=8.001,
                target_alt=50.0,
                target_speed=10.0,
            )
            context = MagicMock()
            response = await servicer.Decide(request, context)

            assert response.advisory is not None
            assert response.advisory.heading_deg == 90.0
            assert response.advisory.mode == "GUIDED"
            assert response.safety is not None
            assert response.safety.safe is True

    @pytest.mark.asyncio
    async def test_decide_safety_violation_rtl(self, servicer, mock_mavlink_telemetry):
        """Test Decide returns RTL advisory on safety violation."""
        mock_mavlink_telemetry.remaining_pct = 10.0  # Below reserve

        with (
            patch(
                "src.dfb.grpc_service.get_telemetry_state",
                return_value=mock_mavlink_telemetry,
            ),
            patch("src.dfb.grpc_service.get_crsf_state") as mock_crsf,
            patch("src.dfb.grpc_service.estimate_state") as mock_estimate,
            patch("src.dfb.grpc_service.check_safety") as mock_safety,
            patch("src.dfb.grpc_service.get_advisor") as mock_get_advisor,
        ):
            mock_crsf.return_value = MagicMock(link_ok=False)
            mock_state = MagicMock(
                valid=True,
                up=50.0,
                ve=10.0,
                vn=0.0,
                vu=0.0,
                yaw=1.57,
                roll=0.0,
                pitch=0.0,
                flight_mode="GUIDED",
                armed=True,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                _raw=mock_mavlink_telemetry,
            )
            mock_estimate.return_value = mock_state
            mock_safety.return_value = SafetyStatus(
                safe=False,
                violations=[
                    SafetyViolation(
                        "BATTERY",
                        "Battery 10.0% below reserve 20.0%",
                        "CRITICAL",
                        10.0,
                        20.0,
                    )
                ],
                warnings=[],
                battery_pct=10.0,
                link_ok=True,
                link_age_s=0.1,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                ground_speed=10.0,
                climb_rate=0.0,
                alt_agl=50.0,
            )
            mock_advisor = MagicMock()
            mock_advisor.advise.return_value = Advisory(
                heading_deg=180.0,
                altitude_m=50.0,
                speed_mps=10.0,
                mode="RTL",
                reason="Safety violation: BATTERY: Battery 10.0% below reserve 20.0%",
                distance_to_target=0.0,
                bearing_to_target=0.0,
                safety=mock_safety.return_value,
            )
            mock_get_advisor.return_value = mock_advisor

            request = flybrain_pb2.DecideRequest(
                use_telemetry=True,
                target_lat=47.001,
                target_lon=8.001,
                target_alt=50.0,
                target_speed=10.0,
            )
            context = MagicMock()
            response = await servicer.Decide(request, context)

            assert response.advisory is not None
            assert response.advisory.mode == "RTL"
            assert "Safety violation" in response.advisory.reason
            assert response.safety.safe is False

    @pytest.mark.asyncio
    async def test_issue_token(self, servicer):
        """Test IssueToken RPC."""
        request = flybrain_pb2.TokenRequest()
        context = MagicMock()
        response = await servicer.IssueToken(request, context)
        assert response.token is not None
        assert len(response.token) == 8
        assert response.expires_in == 30.0

    @pytest.mark.asyncio
    async def test_verify_token(self, servicer):
        """Test VerifyToken RPC."""
        request = flybrain_pb2.VerifyRequest(token="test_token")
        context = MagicMock()
        response = await servicer.VerifyToken(request, context)
        # Token store not shared with HTTP, so returns invalid
        assert response.valid is False
        assert response.expires_in == 0.0

    @pytest.mark.asyncio
    async def test_send_command(self, servicer):
        """Test SendCommand RPC."""
        request = flybrain_pb2.CommandRequest(action="ARM", params={})
        context = MagicMock()
        response = await servicer.SendCommand(request, context)
        assert response.success is True
        assert "ARM" in response.message

    @pytest.mark.asyncio
    async def test_build_mavlink_telemetry(self, servicer, mock_mavlink_telemetry):
        """Test _build_mavlink_telemetry helper."""
        result = servicer._build_mavlink_telemetry(mock_mavlink_telemetry)
        assert result is not None
        # Check nested Position message
        assert result.position.lat == 47.0
        assert result.position.lon == 8.0
        assert result.position.alt == 100.0  # Converted from mm
        assert result.position.relative_alt == 50.0
        assert result.attitude.roll == 0.1

    @pytest.mark.asyncio
    async def test_build_mavlink_telemetry_empty(self, servicer):
        """Test _build_mavlink_telemetry with empty telemetry."""
        empty_telemetry = TelemetryState()
        result = servicer._build_mavlink_telemetry(empty_telemetry)
        assert result is None

    @pytest.mark.asyncio
    async def test_build_crsf_telemetry(self, servicer, mock_crsf_telemetry):
        """Test _build_crsf_telemetry helper."""
        result = servicer._build_crsf_telemetry(mock_crsf_telemetry)
        assert result is not None
        assert result.rssi == -50
        assert result.lq == 90
        assert result.snr == 10
        assert len(result.rc_channels) == 16

    @pytest.mark.asyncio
    async def test_build_crsf_telemetry_with_gps(self, servicer):
        """Test _build_crsf_telemetry with GPS data."""
        crsf = CRSFTelemetry(
            timestamp=time.time(),
            link_ok=True,
            channels=[0.0] * 16,
            rssi=-60,
            lq=80,
            snr=5,
            gps={"lat": 47.0, "lon": 8.0, "alt": 100, "speed": 10.0, "satellites": 8},
        )
        result = servicer._build_crsf_telemetry(crsf)
        assert result is not None
        assert result.gps is not None
        assert result.gps.lat == 47.0
        assert result.gps.satellites == 8

    @pytest.mark.asyncio
    async def test_determine_primary_source(self, servicer):
        """Test _determine_primary_source logic."""
        # Both OK -> mavlink
        mav = TelemetryState(timestamp=time.time(), link_ok=True)
        crsf = CRSFTelemetry(timestamp=time.time(), link_ok=True)
        assert servicer._determine_primary_source(mav, crsf) == "mavlink"

        # Only CRSF OK
        mav.link_ok = False
        assert servicer._determine_primary_source(mav, crsf) == "crsf"

        # Only MAVLink OK
        mav.link_ok = True
        crsf.link_ok = False
        assert servicer._determine_primary_source(mav, crsf) == "mavlink"

        # Neither OK
        mav.link_ok = False
        assert servicer._determine_primary_source(mav, crsf) == "none"


class TestGrpcServer:
    """Tests for gRPC server setup."""

    @pytest.mark.asyncio
    async def test_create_grpc_server_insecure(self):
        """Test creating insecure gRPC server."""
        from src.dfb.grpc_server import create_grpc_server

        server = await create_grpc_server(port=0, enable_tls=False)
        assert server is not None
        await server.stop(0)

    @pytest.mark.asyncio
    async def test_create_grpc_server_secure(self):
        """Test creating secure gRPC server with valid certs."""
        if not CRYPTOGRAPHY_AVAILABLE:
            pytest.skip("cryptography not available")

        import os
        import tempfile

        from src.dfb.grpc_server import create_grpc_server

        # Create valid self-signed cert for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_file = os.path.join(tmpdir, "cert.pem")
            key_file = os.path.join(tmpdir, "key.pem")

            # Generate self-signed cert
            import datetime

            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID

            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name(
                [x509.NameAttribute(NameOID.COMMON_NAME, "test")]
            )
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(
                    datetime.datetime.utcnow() + datetime.timedelta(days=1)
                )
                .add_extension(
                    x509.SubjectAlternativeName([x509.DNSName("localhost")]),
                    critical=False,
                )
                .sign(key, hashes.SHA256())
            )

            with open(key_file, "wb") as f:
                f.write(
                    key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            server = await create_grpc_server(
                port=0, enable_tls=True, cert_file=cert_file, key_file=key_file
            )
            assert server is not None
            await server.stop(0)


class TestGrpcServiceEdgeCases:
    """Tests for gRPC service edge cases."""

    @pytest.fixture
    def servicer(self):
        return FlyBrainServicer()

    @pytest.fixture
    def mock_mavlink_telemetry(self):
        """Create mock MAVLink telemetry."""
        return TelemetryState(
            timestamp=time.time(),
            link_ok=True,
            lat=47.0,
            lon=8.0,
            alt=100000,
            relative_alt=50000,
            roll=0.1,
            pitch=0.0,
            yaw=1.57,
            vx=100,
            vy=0,
            vz=0,
            voltage_v=12.0,
            current_a=5.0,
            remaining_pct=80.0,
            rc_channels=[0.0] * 16,
            msg_counts={"HEARTBEAT": 10},
            flight_mode="GUIDED",
            armed=True,
            autopilot=3,
        )

    @pytest.mark.asyncio
    async def test_decide_manual_mode(self, servicer, mock_mavlink_telemetry):
        """Test Decide in MANUAL mode returns ADVISORY."""
        mock_mavlink_telemetry.flight_mode = "MANUAL"

        with (
            patch(
                "src.dfb.grpc_service.get_telemetry_state",
                return_value=mock_mavlink_telemetry,
            ),
            patch("src.dfb.grpc_service.get_crsf_state") as mock_crsf,
            patch("src.dfb.grpc_service.estimate_state") as mock_estimate,
            patch("src.dfb.grpc_service.check_safety") as mock_safety,
            patch("src.dfb.grpc_service.get_advisor") as mock_get_advisor,
        ):
            mock_crsf.return_value = MagicMock(link_ok=False)
            mock_estimate.return_value = MagicMock(
                valid=True,
                up=50.0,
                ve=10.0,
                vn=0.0,
                vu=0.0,
                yaw=1.57,
                roll=0.0,
                pitch=0.0,
                flight_mode="MANUAL",
                armed=True,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                _raw=mock_mavlink_telemetry,
            )
            mock_safety.return_value = SafetyStatus(
                safe=True,
                violations=[],
                warnings=[],
                battery_pct=80.0,
                link_ok=True,
                link_age_s=0.1,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                ground_speed=10.0,
                climb_rate=0.0,
                alt_agl=50.0,
            )
            mock_advisor = MagicMock()
            mock_advisor.advise.return_value = Advisory(
                heading_deg=90.0,
                altitude_m=50.0,
                speed_mps=10.0,
                mode="ADVISORY",
                reason="Navigating to target (pilot in control)",
                distance_to_target=1000.0,
                bearing_to_target=90.0,
                safety=mock_safety.return_value,
            )
            mock_get_advisor.return_value = mock_advisor

            request = flybrain_pb2.DecideRequest(
                use_telemetry=True,
                target_lat=47.001,
                target_lon=8.001,
                target_alt=50.0,
                target_speed=10.0,
            )
            context = MagicMock()
            response = await servicer.Decide(request, context)

            assert response.advisory.mode == "ADVISORY"
            assert "pilot in control" in response.advisory.reason

    @pytest.mark.asyncio
    async def test_decide_auto_safety_mode(self, servicer, mock_mavlink_telemetry):
        """Test Decide in RTL mode doesn't interfere."""
        mock_mavlink_telemetry.flight_mode = "RTL"

        with (
            patch(
                "src.dfb.grpc_service.get_telemetry_state",
                return_value=mock_mavlink_telemetry,
            ),
            patch("src.dfb.grpc_service.get_crsf_state") as mock_crsf,
            patch("src.dfb.grpc_service.estimate_state") as mock_estimate,
            patch("src.dfb.grpc_service.check_safety") as mock_safety,
            patch("src.dfb.grpc_service.get_advisor") as mock_get_advisor,
        ):
            mock_crsf.return_value = MagicMock(link_ok=False)
            mock_estimate.return_value = MagicMock(
                valid=True,
                up=50.0,
                ve=0.0,
                vn=0.0,
                vu=0.0,
                yaw=1.57,
                roll=0.0,
                pitch=0.0,
                flight_mode="RTL",
                armed=True,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                _raw=mock_mavlink_telemetry,
            )
            mock_safety.return_value = SafetyStatus(
                safe=True,
                violations=[],
                warnings=[],
                battery_pct=80.0,
                link_ok=True,
                link_age_s=0.1,
                gps_fix_type=3,
                hdop=1.0,
                vdop=1.0,
                ground_speed=0.0,
                climb_rate=0.0,
                alt_agl=50.0,
            )
            mock_advisor = MagicMock()
            mock_advisor.advise.return_value = Advisory(
                heading_deg=0.0,
                altitude_m=50.0,
                speed_mps=0.0,
                mode="RTL",
                reason="FC in automatic safety mode: RTL",
                distance_to_target=0.0,
                bearing_to_target=0.0,
                safety=mock_safety.return_value,
            )
            mock_get_advisor.return_value = mock_advisor

            request = flybrain_pb2.DecideRequest(use_telemetry=True)
            context = MagicMock()
            response = await servicer.Decide(request, context)

            assert response.advisory.mode == "RTL"
            assert "automatic safety mode" in response.advisory.reason
