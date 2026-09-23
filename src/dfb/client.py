"""Typed client for Deck Fly Brain service."""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests

if TYPE_CHECKING:
    import grpc
else:
    try:
        import grpc
    except ImportError:
        grpc = None


@dataclass
class HealthResponse:
    status: str
    version: str


@dataclass
class VersionResponse:
    version: str


@dataclass
class DecideResponse:
    action: str
    confidence: float
    logits: Optional[List[float]] = None


@dataclass
class AdvisoryResponse:
    heading_deg: float
    altitude_m: float
    speed_mps: float
    mode: str
    reason: str
    distance_to_target: Optional[float] = None
    bearing_to_target: Optional[float] = None


@dataclass
class SafetyViolationResponse:
    category: str
    message: str
    severity: str
    value: float
    limit: float


@dataclass
class SafetyStatusResponse:
    safe: bool
    violations: List[SafetyViolationResponse]
    warnings: List[SafetyViolationResponse]
    battery_pct: float
    link_ok: bool
    link_age_s: float
    gps_fix_type: int
    hdop: float
    vdop: float
    ground_speed: float
    climb_rate: float
    alt_agl: float


@dataclass
class TelemetryDecideResponse:
    advisory: Optional[AdvisoryResponse] = None
    safety: Optional[SafetyStatusResponse] = None
    # Legacy fields
    action: Optional[str] = None
    confidence: Optional[float] = None
    logits: Optional[List[float]] = None


@dataclass
class CRSFTelemetryResponse:
    timestamp: float
    link_ok: bool
    rc_channels: List[float]
    rssi: Optional[float] = None
    lq: Optional[float] = None
    snr: Optional[float] = None
    rf_mode: Optional[int] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    capacity: Optional[float] = None
    gps: Optional[Dict[str, Any]] = None
    message_counts: Dict[str, int] = None  # type: ignore[assignment]


@dataclass
class MAVLinkTelemetryResponse:
    timestamp: float
    link_ok: bool
    position: Dict[str, float]
    attitude: Dict[str, float]
    velocity: Dict[str, float]
    battery: Dict[str, float]
    rc_channels: List[float]
    message_counts: Dict[str, int]
    flight_mode: str
    armed: bool


@dataclass
class FusedTelemetryResponse:
    rc_channels: List[float]
    timestamp: float


@dataclass
class TelemetryResponse:
    primary_source: str
    mavlink: Optional[MAVLinkTelemetryResponse] = None
    crsf: Optional[CRSFTelemetryResponse] = None
    fused: Optional[FusedTelemetryResponse] = None


@dataclass
class TokenResponse:
    token: str
    expires_in: float


@dataclass
class CommandResponse:
    success: bool
    message: str


@dataclass
class VerifyResponse:
    valid: bool
    expires_in: float


class GrpcDeckClient:
    """gRPC client for Deck Fly Brain service."""

    def __init__(
        self,
        host: str = "steamdeck",
        port: int = 8083,
        timeout: float = 5.0,
        tls: bool = False,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls = tls
        self.cert_file = cert_file
        self.key_file = key_file
        self._channel: Optional["grpc.aio.Channel"] = None
        self._stub = None

    async def _get_channel(self) -> "grpc.aio.Channel":
        if self._channel is None:
            if self.tls:
                if self.cert_file and self.key_file:
                    with open(self.cert_file, "rb") as f:
                        cert = f.read()
                    with open(self.key_file, "rb") as f:
                        key = f.read()
                    credentials = grpc.ssl_channel_credentials(
                        root_certificates=cert,
                        private_key=key,
                    )
                else:
                    credentials = grpc.ssl_channel_credentials()
                self._channel = grpc.aio.secure_channel(
                    f"{self.host}:{self.port}", credentials
                )
            else:
                self._channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
        return self._channel

    async def _get_stub(self):
        if self._stub is None:
            channel = await self._get_channel()
            from src.dfb.grpc import flybrain_pb2_grpc

            self._stub = flybrain_pb2_grpc.FlyBrainServiceStub(channel)
        return self._stub

    async def close(self):
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def health(self) -> HealthResponse:
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        response = await stub.GetHealth(flybrain_pb2.HealthRequest())
        return HealthResponse(status=response.status, version=response.version)

    async def version(self) -> VersionResponse:
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        response = await stub.GetVersion(flybrain_pb2.VersionRequest())
        return VersionResponse(version=response.version)

    async def telemetry(self) -> TelemetryResponse:
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        response = await stub.GetTelemetry(flybrain_pb2.TelemetryRequest())
        return self._convert_telemetry(response)

    def _convert_telemetry(self, response) -> TelemetryResponse:
        mavlink = None
        if response.mavlink:
            m = response.mavlink
            mavlink = MAVLinkTelemetryResponse(
                timestamp=m.timestamp,
                link_ok=m.link_ok,
                position=m.position,
                attitude=m.attitude,
                velocity=m.velocity,
                battery=m.battery,
                rc_channels=list(m.rc_channels),
                message_counts=dict(m.message_counts),
                flight_mode=m.flight_mode,
                armed=m.armed,
            )

        crsf = None
        if response.crsf:
            c = response.crsf
            crsf = CRSFTelemetryResponse(
                timestamp=c.timestamp,
                link_ok=c.link_ok,
                rc_channels=list(c.rc_channels),
                rssi=c.get("rssi"),
                lq=c.get("lq"),
                snr=c.get("snr"),
                rf_mode=c.get("rf_mode"),
                voltage=c.get("voltage"),
                current=c.get("current"),
                capacity=c.get("capacity"),
                gps=c.get("gps"),
                message_counts=dict(c.message_counts),
            )

        fused = None
        if response.fused:
            f = response.fused
            fused = FusedTelemetryResponse(
                rc_channels=list(f.rc_channels),
                timestamp=f.timestamp,
            )

        return TelemetryResponse(
            primary_source=response.source,
            mavlink=mavlink,
            crsf=crsf,
            fused=fused,
        )

    async def decide_telemetry(
        self,
        target_lat: Optional[float] = None,
        target_lon: Optional[float] = None,
        target_alt: Optional[float] = None,
        target_speed: Optional[float] = None,
    ) -> TelemetryDecideResponse:
        """Request telemetry-aware advisory decision via gRPC."""
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        request = flybrain_pb2.DecideRequest(
            use_telemetry=True,
            target_lat=target_lat or 0.0,
            target_lon=target_lon or 0.0,
            target_alt=target_alt or 50.0,
            target_speed=target_speed or 10.0,
        )
        response = await stub.Decide(request)

        advisory = None
        if response.advisory:
            adv = response.advisory
            advisory = AdvisoryResponse(
                heading_deg=adv.heading_deg,
                altitude_m=adv.altitude_m,
                speed_mps=adv.speed_mps,
                mode=adv.mode,
                reason=adv.reason,
                distance_to_target=adv.distance_to_target,
                bearing_to_target=adv.bearing_to_target,
            )

        safety = None
        if response.safety:
            s = response.safety
            safety = SafetyStatusResponse(
                safe=s.safe,
                violations=[SafetyViolationResponse(**vars(v)) for v in s.violations],
                warnings=[SafetyViolationResponse(**vars(v)) for v in s.warnings],
                battery_pct=s.battery_pct,
                link_ok=s.link_ok,
                link_age_s=s.link_age_s,
                gps_fix_type=s.gps_fix_type,
                hdop=s.hdop,
                vdop=s.vdop,
                ground_speed=s.ground_speed,
                climb_rate=s.climb_rate,
                alt_agl=s.alt_agl,
            )

        return TelemetryDecideResponse(
            advisory=advisory,
            safety=safety,
            action=response.action,
            confidence=response.confidence,
            logits=list(response.logits),
        )

    async def issue_token(self) -> TokenResponse:
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        response = await stub.IssueToken(flybrain_pb2.TokenRequest())
        return TokenResponse(token=response.token, expires_in=response.expires_in)

    async def command(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
    ) -> CommandResponse:
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        request = flybrain_pb2.CommandRequest(
            action=action,
            params=params or {},
        )
        response = await stub.SendCommand(request)
        return CommandResponse(success=response.success, message=response.message)

    async def verify_token(self, token: str) -> VerifyResponse:
        stub = await self._get_stub()
        from src.dfb.grpc import flybrain_pb2

        response = await stub.VerifyToken(flybrain_pb2.VerifyRequest(token=token))
        return VerifyResponse(valid=response.valid, expires_in=response.expires_in)


class HttpDeckClient:
    """Client for Deck Fly Brain REST API."""

    def __init__(
        self,
        host: str = "steamdeck",
        port: int = 8082,
        timeout: float = 5.0,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get(self, path: str) -> Dict[str, Any]:
        resp = self.session.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        resp = self.session.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def health(self) -> HealthResponse:
        data = self._get("/health")
        return HealthResponse(status=data["status"], version=data["version"])

    def version(self) -> VersionResponse:
        data = self._get("/version")
        return VersionResponse(version=data["version"])

    def telemetry(self) -> TelemetryResponse:
        """Get unified telemetry state (MAVLink + CRSF)."""
        data = self._get("/telemetry")
        mavlink = None
        if data.get("mavlink"):
            m = data["mavlink"]
            mavlink = MAVLinkTelemetryResponse(
                timestamp=m["timestamp"],
                link_ok=m["link_ok"],
                position=m["position"],
                attitude=m["attitude"],
                velocity=m["velocity"],
                battery=m["battery"],
                rc_channels=m["rc_channels"],
                message_counts=m["message_counts"],
                flight_mode=m["flight_mode"],
                armed=m["armed"],
            )

        crsf = None
        if data.get("crsf"):
            c = data["crsf"]
            crsf = CRSFTelemetryResponse(
                timestamp=c["timestamp"],
                link_ok=c["link_ok"],
                rc_channels=c["rc_channels"],
                rssi=c.get("rssi"),
                lq=c.get("lq"),
                snr=c.get("snr"),
                rf_mode=c.get("rf_mode"),
                voltage=c.get("voltage"),
                current=c.get("current"),
                capacity=c.get("capacity"),
                gps=c.get("gps"),
                message_counts=c["message_counts"],
            )

        fused = None
        if data.get("fused"):
            f = data["fused"]
            fused = FusedTelemetryResponse(
                rc_channels=f["rc_channels"],
                timestamp=f["timestamp"],
            )

        return TelemetryResponse(
            primary_source=data["primary_source"],
            mavlink=mavlink,
            crsf=crsf,
            fused=fused,
        )

    def decide(
        self,
        position: List[int],
        grid: List[List[int]],
        exit: List[int],
    ) -> DecideResponse:
        payload = {"position": position, "grid": grid, "exit": exit}
        data = self._post("/decide", payload)
        return DecideResponse(
            action=data["action"],
            confidence=data["confidence"],
            logits=data.get("logits"),
        )

    def decide_telemetry(
        self,
        target_lat: Optional[float] = None,
        target_lon: Optional[float] = None,
        target_alt: Optional[float] = None,
        target_speed: Optional[float] = None,
    ) -> TelemetryDecideResponse:
        """Request telemetry-aware advisory decision."""
        payload = {
            "use_telemetry": True,
            "target_lat": target_lat,
            "target_lon": target_lon,
            "target_alt": target_alt,
            "target_speed": target_speed,
        }
        data = self._post("/decide", payload)

        advisory = None
        if data.get("advisory"):
            adv = data["advisory"]
            advisory = AdvisoryResponse(
                heading_deg=adv["heading_deg"],
                altitude_m=adv["altitude_m"],
                speed_mps=adv["speed_mps"],
                mode=adv["mode"],
                reason=adv["reason"],
                distance_to_target=adv.get("distance_to_target"),
                bearing_to_target=adv.get("bearing_to_target"),
            )

        safety = None
        if data.get("safety"):
            s = data["safety"]
            safety = SafetyStatusResponse(
                safe=s["safe"],
                violations=[SafetyViolationResponse(**v) for v in s["violations"]],
                warnings=[SafetyViolationResponse(**v) for v in s["warnings"]],
                battery_pct=s["battery_pct"],
                link_ok=s["link_ok"],
                link_age_s=s["link_age_s"],
                gps_fix_type=s["gps_fix_type"],
                hdop=s["hdop"],
                vdop=s["vdop"],
                ground_speed=s["ground_speed"],
                climb_rate=s["climb_rate"],
                alt_agl=s["alt_agl"],
            )

        return TelemetryDecideResponse(
            advisory=advisory,
            safety=safety,
            action=data.get("action"),
            confidence=data.get("confidence"),
            logits=data.get("logits"),
        )

    def issue_token(self) -> TokenResponse:
        data = self._post("/confirm/issue", {})
        return TokenResponse(token=data["token"], expires_in=data["expires_in"])

    def command(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
    ) -> CommandResponse:
        headers = {}
        if token:
            headers["X-Confirmation-Token"] = token
        payload = {"action": action, "params": params or {}}
        data = self._post("/command", payload, headers=headers)
        return CommandResponse(success=data["success"], message=data["message"])

    def verify_token(self, token: str) -> VerifyResponse:
        data = self._get(f"/confirm/verify/{token}")
        return VerifyResponse(valid=data["valid"], expires_in=data["expires_in"])


def create_client_from_env() -> HttpDeckClient:
    """Create client using DFB_HOST/DFB_PORT env vars."""
    host = os.getenv("DFB_HOST", "steamdeck")
    port = int(os.getenv("DFB_PORT", "8082"))
    return HttpDeckClient(host=host, port=port)
