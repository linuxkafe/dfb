"""gRPC service implementation for FlyBrain."""

import asyncio
import uuid
from typing import Optional

from src.dfb import __version__
from src.dfb.advisor import MissionGoal, get_advisor
from src.dfb.cpu_engine import get_cpu_engine
from src.dfb.crsf_ingest import get_crsf_state

# Import generated gRPC code
from src.dfb.grpc import flybrain_pb2, flybrain_pb2_grpc
from src.dfb.health import get_overall_health
from src.dfb.mavlink_ingest import get_telemetry_state
from src.dfb.safety_envelope import check_safety
from src.dfb.state_estimator import estimate_state


class FlyBrainServicer(flybrain_pb2_grpc.FlyBrainServiceServicer):
    """gRPC service implementation for FlyBrain."""

    def __init__(self):
        self._cpu_engine = None
        self._advisor = None

    def _get_cpu_engine(self):
        if self._cpu_engine is None:
            self._cpu_engine = get_cpu_engine()
        return self._cpu_engine

    def _get_advisor(self):
        if self._advisor is None:
            self._advisor = get_advisor()
        return self._advisor

    def _build_mavlink_telemetry(
        self, telemetry
    ) -> Optional["flybrain_pb2.TelemetryMavlink"]:
        """Convert MAVLink telemetry to protobuf."""
        if telemetry.timestamp == 0.0:
            return None

        return flybrain_pb2.TelemetryMavlink(
            timestamp=telemetry.timestamp,
            link_ok=telemetry.link_ok,
            position=flybrain_pb2.Position(
                lat=telemetry.lat,
                lon=telemetry.lon,
                alt=telemetry.alt / 1000.0,
                relative_alt=telemetry.relative_alt / 1000.0,
            ),
            attitude=flybrain_pb2.Attitude(
                roll=telemetry.roll,
                pitch=telemetry.pitch,
                yaw=telemetry.yaw,
            ),
            velocity=flybrain_pb2.Velocity(
                vx=telemetry.vx / 100.0,
                vy=telemetry.vy / 100.0,
                vz=telemetry.vz / 100.0,
            ),
            battery=flybrain_pb2.Battery(
                voltage_v=telemetry.voltage_v,
                current_a=telemetry.current_a,
                remaining_pct=telemetry.remaining_pct,
            ),
            rc_channels=telemetry.rc_channels,
            message_counts=telemetry.msg_counts,
            flight_mode=telemetry.flight_mode,
            armed=telemetry.armed,
        )

    def _build_crsf_telemetry(
        self, telemetry
    ) -> Optional["flybrain_pb2.TelemetryCrsf"]:
        """Convert CRSF telemetry to protobuf."""
        if telemetry.timestamp == 0.0:
            return None

        gps = None
        if telemetry.gps:
            gps = flybrain_pb2.GPS(
                lat=telemetry.gps.get("lat", 0.0),
                lon=telemetry.gps.get("lon", 0.0),
                alt=telemetry.gps.get("alt", 0.0),
                speed=telemetry.gps.get("speed", 0.0),
                satellites=telemetry.gps.get("satellites", 0),
            )

        return flybrain_pb2.TelemetryCrsf(
            timestamp=telemetry.timestamp,
            link_ok=telemetry.link_ok,
            rc_channels=telemetry.channels,
            rssi=telemetry.rssi,
            lq=telemetry.lq,
            snr=telemetry.snr,
            rf_mode=telemetry.rf_mode,
            voltage=telemetry.voltage,
            current=telemetry.current,
            capacity=telemetry.capacity,
            gps=gps,
            message_counts=telemetry.msg_counts,
        )

    def _build_fused_telemetry(
        self, crsf_telemetry
    ) -> Optional["flybrain_pb2.TelemetryFused"]:
        """Build fused telemetry from CRSF."""
        if crsf_telemetry.timestamp == 0.0:
            return None
        return flybrain_pb2.TelemetryFused(
            rc_channels=crsf_telemetry.channels,
            timestamp=crsf_telemetry.timestamp,
        )

    def _determine_primary_source(self, mavlink_telemetry, crsf_telemetry) -> str:
        """Determine primary telemetry source."""
        mav_ok = mavlink_telemetry.timestamp > 0.0 and mavlink_telemetry.link_ok
        crsf_ok = crsf_telemetry.timestamp > 0.0 and crsf_telemetry.link_ok

        if crsf_ok and not mav_ok:
            return "crsf"
        elif mav_ok and not crsf_ok:
            return "mavlink"
        elif mav_ok and crsf_ok:
            return "mavlink"  # Default to MAVLink when both available
        return "none"

    def _build_telemetry_response(
        self, mavlink_telemetry, crsf_telemetry
    ) -> "flybrain_pb2.TelemetryResponse":
        """Build complete telemetry response."""
        primary = self._determine_primary_source(mavlink_telemetry, crsf_telemetry)

        return flybrain_pb2.TelemetryResponse(
            timestamp=mavlink_telemetry.timestamp
            if mavlink_telemetry.timestamp > 0
            else crsf_telemetry.timestamp,
            link_ok=mavlink_telemetry.link_ok or crsf_telemetry.link_ok,
            source=primary,
            mavlink=self._build_mavlink_telemetry(mavlink_telemetry),
            crsf=self._build_crsf_telemetry(crsf_telemetry),
            fused=self._build_fused_telemetry(crsf_telemetry),
        )

    def _build_advisory(self, advisory) -> "flybrain_pb2.Advisory":
        return flybrain_pb2.Advisory(
            heading_deg=advisory.heading_deg,
            altitude_m=advisory.altitude_m,
            speed_mps=advisory.speed_mps,
            mode=advisory.mode,
            reason=advisory.reason,
            distance_to_target=advisory.distance_to_target or 0.0,
            bearing_to_target=advisory.bearing_to_target or 0.0,
        )

    def _build_safety_status(self, safety) -> "flybrain_pb2.SafetyStatus":
        violations = [
            flybrain_pb2.SafetyViolation(
                category=v.category,
                message=v.message,
                severity=v.severity,
                value=v.value,
                limit=v.limit,
            )
            for v in safety.violations
        ]
        warnings = [
            flybrain_pb2.SafetyViolation(
                category=v.category,
                message=v.message,
                severity=v.severity,
                value=v.value,
                limit=v.limit,
            )
            for v in safety.warnings
        ]
        return flybrain_pb2.SafetyStatus(
            safe=safety.safe,
            violations=violations,
            warnings=warnings,
            battery_pct=safety.battery_pct,
            link_ok=safety.link_ok,
            link_age_s=safety.link_age_s,
            gps_fix_type=safety.gps_fix_type,
            hdop=safety.hdop,
            vdop=safety.vdop,
            ground_speed=safety.ground_speed,
            climb_rate=safety.climb_rate,
            alt_agl=safety.alt_agl,
        )

    async def GetHealth(self, request, context):
        overall, components = get_overall_health()
        return flybrain_pb2.HealthResponse(
            status=overall,
            version=__version__,
        )

    async def GetVersion(self, request, context):
        return flybrain_pb2.VersionResponse(version=__version__)

    async def GetTelemetry(self, request, context):
        mavlink_telemetry = get_telemetry_state()
        crsf_telemetry = get_crsf_state()
        return self._build_telemetry_response(mavlink_telemetry, crsf_telemetry)

    async def GetTelemetryStream(self, request, context):
        interval_ms = request.interval_ms if request.interval_ms > 0 else 100
        interval = max(0.02, interval_ms / 1000.0)

        while context.is_active():
            mavlink_telemetry = get_telemetry_state()
            crsf_telemetry = get_crsf_state()
            response = self._build_telemetry_response(mavlink_telemetry, crsf_telemetry)
            yield response
            await asyncio.sleep(interval)

    def _estimate_state(self, telemetry):
        """Estimate state from telemetry."""
        return estimate_state(telemetry)

    def _compute_advisory(self, state, request) -> "flybrain_pb2.Advisory":
        """Compute advisory from state and request."""
        # Create MissionGoal for advisor (Python class)
        mission_goal = MissionGoal(
            target_lat=request.target_lat if request.target_lat != 0 else None,
            target_lon=request.target_lon if request.target_lon != 0 else None,
            target_alt=request.target_alt if request.target_alt > 0 else 50.0,
            target_speed=request.target_speed if request.target_speed > 0 else 10.0,
        )

        # Get advisor and compute advisory
        advisor = self._get_advisor()
        state.flight_mode = state.flight_mode or "UNKNOWN"
        advisory = advisor.advise(state, mission_goal)

        # Convert to protobuf
        return flybrain_pb2.Advisory(
            heading_deg=advisory.heading_deg,
            altitude_m=advisory.altitude_m,
            speed_mps=advisory.speed_mps,
            mode=advisory.mode,
            reason=advisory.reason,
            distance_to_target=advisory.distance_to_target or 0.0,
            bearing_to_target=advisory.bearing_to_target or 0.0,
        )

    async def Decide(self, request, context):
        # Get telemetry from both sources
        mavlink_telemetry = get_telemetry_state()
        crsf_telemetry = get_crsf_state()

        # Use MAVLink for state estimation (FC EKF data)
        state = self._estimate_state(mavlink_telemetry)
        state.flight_mode = mavlink_telemetry.flight_mode
        state.armed = mavlink_telemetry.armed

        # Use CRSF RC channels if available (higher rate, more precise)
        if crsf_telemetry.link_ok and crsf_telemetry.channels:
            # For now, we don't override state.rc_channels in EstimatedState
            # but the advisor could use them
            pass

        # Safety check
        safety = check_safety(state)

        # Build mission goal
        mission_goal = MissionGoal(
            target_lat=request.target_lat if request.target_lat != 0 else None,
            target_lon=request.target_lon if request.target_lon != 0 else None,
            target_alt=request.target_alt if request.target_alt > 0 else 50.0,
            target_speed=request.target_speed if request.target_speed > 0 else 10.0,
        )

        # Get advisor
        advisor = self._get_advisor()
        advisory = advisor.advise(state, mission_goal)

        # Build response
        advisory_pb = flybrain_pb2.Advisory(
            heading_deg=advisory.heading_deg,
            altitude_m=advisory.altitude_m,
            speed_mps=advisory.speed_mps,
            mode=advisory.mode,
            reason=advisory.reason,
            distance_to_target=advisory.distance_to_target or 0.0,
            bearing_to_target=advisory.bearing_to_target or 0.0,
        )

        safety_pb = flybrain_pb2.SafetyStatus(
            safe=safety.safe,
            violations=[
                flybrain_pb2.SafetyViolation(
                    category=v.category,
                    message=v.message,
                    severity=v.severity,
                    value=v.value,
                    limit=v.limit,
                )
                for v in safety.violations
            ],
            warnings=[
                flybrain_pb2.SafetyViolation(
                    category=v.category,
                    message=v.message,
                    severity=v.severity,
                    value=v.value,
                    limit=v.limit,
                )
                for v in safety.warnings
            ],
            battery_pct=safety.battery_pct,
            link_ok=safety.link_ok,
            link_age_s=safety.link_age_s,
            gps_fix_type=safety.gps_fix_type,
            hdop=safety.hdop,
            vdop=safety.vdop,
            ground_speed=safety.ground_speed,
            climb_rate=safety.climb_rate,
            alt_agl=safety.alt_agl,
        )

        # Record metrics (reuse existing metrics from service module)
        return flybrain_pb2.DecideResponse(
            advisory=advisory_pb,
            safety=safety_pb,
        )

    async def IssueToken(self, request, context):
        token = str(uuid.uuid4())[:8]
        # Note: In production, this would need shared token store with HTTP API
        return flybrain_pb2.TokenResponse(token=token, expires_in=30.0)

    async def VerifyToken(self, request, context):
        # Would need shared token store
        return flybrain_pb2.VerifyResponse(valid=False, expires_in=0.0)

    async def SendCommand(self, request, context):
        # Safety-critical command - would need token validation
        return flybrain_pb2.CommandResponse(
            success=True, message=f"Command '{request.action}' acknowledged (simulated)"
        )
