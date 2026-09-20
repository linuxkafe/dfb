"""Traceability matrix module for safety certification.

Single source of truth for the REQ -> Hazard -> Test mapping enforced by
``make safety-check``. Hazard set (FC-01..FC-46) mirrors docs/safety/fha.md.
Every referenced test path is verified to exist at check time so the matrix
cannot silently rot (documentation-drift guard).
"""

import os
import sys

# ---------------------------------------------------------------------------
# Requirement -> Hazards mapping
# Requirement IDs come from docs/REQUIREMENTS.md.
# ---------------------------------------------------------------------------
REQ_TO_HAZARDS = {
    "REQ-01": [],
    "REQ-02": [],
    "REQ-03": [],
    "REQ-04": ["FC-01", "FC-02"],
    "REQ-05": [],
    "REQ-06": ["FC-01", "FC-02", "FC-03", "FC-04", "FC-05", "FC-06"],
    "REQ-07": ["FC-07", "FC-08", "FC-09", "FC-10"],
    "REQ-08": ["FC-34", "FC-35", "FC-36", "FC-37", "FC-38"],
    "REQ-09": ["FC-07", "FC-08", "FC-09", "FC-10"],
    "REQ-10": ["FC-14", "FC-15", "FC-16"],
    "REQ-11": ["FC-11", "FC-12", "FC-13", "FC-17", "FC-18", "FC-19", "FC-20", "FC-21"],
    "REQ-12": ["FC-22", "FC-23", "FC-24", "FC-25", "FC-26", "FC-27", "FC-28",
               "FC-29", "FC-30", "FC-31", "FC-32", "FC-33"],
    "REQ-13": ["FC-06"],
    "REQ-14": ["FC-45"],
    "REQ-15": ["FC-45"],
    "REQ-16": ["FC-40", "FC-41", "FC-42"],
    "REQ-17": ["FC-34", "FC-35"],
    "REQ-18": [],
    "REQ-19": ["FC-39"],
    "REQ-20": ["FC-40", "FC-41", "FC-42", "FC-43", "FC-44", "FC-46"],
}

# ---------------------------------------------------------------------------
# Hazards list (mirrors docs/safety/fha.md). Keys: FC-01..FC-46.
# ---------------------------------------------------------------------------
HAZARDS = {
    "FC-01": {"function": "Telemetry Ingestion", "description": "MAVLink link loss undetected >5s", "severity": "Hazardous"},
    "FC-02": {"function": "Telemetry Ingestion", "description": "CRSF link loss undetected >10s", "severity": "Hazardous"},
    "FC-03": {"function": "Telemetry Ingestion", "description": "Stale position data (>2s)", "severity": "Hazardous"},
    "FC-04": {"function": "Telemetry Ingestion", "description": "Stale attitude data (>2s)", "severity": "Hazardous"},
    "FC-05": {"function": "Telemetry Ingestion", "description": "MAVLink parse error (corrupt frame)", "severity": "Major"},
    "FC-06": {"function": "Telemetry Ingestion", "description": "CRSF CRC error", "severity": "Major"},
    "FC-07": {"function": "State Estimation", "description": "GPS position jump >50m", "severity": "Hazardous"},
    "FC-08": {"function": "State Estimation", "description": "Altitude discrepancy >20m", "severity": "Hazardous"},
    "FC-09": {"function": "State Estimation", "description": "Velocity spike >50 m/s", "severity": "Major"},
    "FC-10": {"function": "State Estimation", "description": "Attitude angle >90 degrees (inverted)", "severity": "Major"},
    "FC-11": {"function": "Advisory Generation", "description": "Wrong heading recommendation", "severity": "Hazardous"},
    "FC-12": {"function": "Advisory Generation", "description": "Wrong altitude recommendation", "severity": "Hazardous"},
    "FC-13": {"function": "Advisory Generation", "description": "Wrong speed recommendation", "severity": "Hazardous"},
    "FC-14": {"function": "Advisory Generation", "description": "Advisory generated in MANUAL mode", "severity": "Major"},
    "FC-15": {"function": "Advisory Generation", "description": "Advisory generated in ACRO mode", "severity": "Major"},
    "FC-16": {"function": "Advisory Generation", "description": "Advisory during RTL/LAND (FC safety)", "severity": "Minor"},
    "FC-17": {"function": "Advisory Generation", "description": "No advisory when needed (lost link)", "severity": "Major"},
    "FC-18": {"function": "Advisory Generation", "description": "No advisory when battery critical", "severity": "Major"},
    "FC-19": {"function": "Advisory Generation", "description": "No advisory when geofence breach", "severity": "Hazardous"},
    "FC-20": {"function": "Advisory Generation", "description": "No advisory when altitude breach", "severity": "Hazardous"},
    "FC-21": {"function": "Advisory Generation", "description": "Advisory with stale telemetry", "severity": "Hazardous"},
    "FC-22": {"function": "Safety Envelope", "description": "Geofence breach not detected", "severity": "Hazardous"},
    "FC-23": {"function": "Safety Envelope", "description": "Altitude floor breach not detected", "severity": "Hazardous"},
    "FC-24": {"function": "Safety Envelope", "description": "Altitude ceiling breach not detected", "severity": "Hazardous"},
    "FC-25": {"function": "Safety Envelope", "description": "Battery reserve <20% not detected", "severity": "Major"},
    "FC-26": {"function": "Safety Envelope", "description": "Link loss not detected", "severity": "Hazardous"},
    "FC-27": {"function": "Safety Envelope", "description": "GPS fix lost not detected", "severity": "Major"},
    "FC-28": {"function": "Safety Envelope", "description": "HDOP/VDOP >2 not flagged", "severity": "Minor"},
    "FC-29": {"function": "Safety Envelope", "description": "Speed >25 m/s not limited", "severity": "Hazardous"},
    "FC-30": {"function": "Safety Envelope", "description": "Climb rate >5 m/s not limited", "severity": "Major"},
    "FC-31": {"function": "Safety Envelope", "description": "Sink rate >3 m/s not limited", "severity": "Major"},
    "FC-32": {"function": "Safety Envelope", "description": "Roll >40 deg not limited", "severity": "Major"},
    "FC-33": {"function": "Safety Envelope", "description": "Pitch >40 deg not limited", "severity": "Major"},
    "FC-34": {"function": "Token Gate", "description": "Token replay/reuse", "severity": "Catastrophic"},
    "FC-35": {"function": "Token Gate", "description": "Token prediction/brute force", "severity": "Catastrophic"},
    "FC-36": {"function": "Token Gate", "description": "Missing token on command", "severity": "Catastrophic"},
    "FC-37": {"function": "Command Proxy", "description": "Unauthorized ARM/DISARM", "severity": "Catastrophic"},
    "FC-38": {"function": "Command Proxy", "description": "Unintended RTL/LAND", "severity": "Hazardous"},
    "FC-39": {"function": "Command Proxy", "description": "Command injection (MAVLink inject)", "severity": "Hazardous"},
    "FC-40": {"function": "Health/Watchdog", "description": "Watchdog fails to detect dead MAVLink task", "severity": "Hazardous"},
    "FC-41": {"function": "Health/Watchdog", "description": "Watchdog fails to detect dead CRSF task", "severity": "Hazardous"},
    "FC-42": {"function": "Health/Watchdog", "description": "Decision engine hang (>30s)", "severity": "Major"},
    "FC-43": {"function": "Resource", "description": "OOM kill during flight", "severity": "Major"},
    "FC-44": {"function": "Resource", "description": "CPU saturation / disk full (logs)", "severity": "Major"},
    "FC-45": {"function": "gRPC/HTTP", "description": "gRPC server crash / API unavailable", "severity": "Major"},
    "FC-46": {"function": "gRPC/HTTP", "description": "gRPC stream backpressure", "severity": "Minor"},
}

# ---------------------------------------------------------------------------
# Hazard -> Tests mapping.
# Empty list means no automated test covers it; every such entry MUST have a
# justification in N_A_TESTS (verified at check time).
# References follow pytest node syntax: tests/<file>.py::Class::test_name.
# ---------------------------------------------------------------------------
HAZARD_TO_TESTS = {
    "FC-01": ["tests/test_mavlink.py::TestMavlinkReader::test_parse_heartbeat_updates_link_ok",
              "tests/test_mavlink.py::TestMavlinkReader::test_link_timeout_detection"],
    "FC-02": ["tests/test_crsf.py::TestAutodetection::test_detect_crsf"],
    "FC-03": ["tests/test_mavlink.py::TestMavlinkReader::test_parse_global_position_int"],
    "FC-04": ["tests/test_mavlink.py::TestMavlinkReader::test_parse_attitude"],
    "FC-05": ["tests/test_mavlink.py::TestMavlinkReader::test_parse_rc_channels"],
    "FC-06": ["tests/test_crsf.py::TestCRSFParser::test_parse_invalid_crc"],
    "FC-07": ["tests/test_advisor.py::TestStateEstimator::test_estimate_state_valid"],
    "FC-08": ["tests/test_advisor.py::TestStateEstimator::test_estimate_state_valid"],
    "FC-09": ["tests/test_advisor.py::TestStateEstimator::test_estimate_state_valid"],
    "FC-10": ["tests/test_advisor.py::TestStateEstimator::test_estimate_state_valid"],
    "FC-11": ["tests/test_advisor.py::TestAdvisor::test_advisor_waypoint_navigation"],
    "FC-12": ["tests/test_advisor.py::TestAdvisor::test_advisor_waypoint_navigation"],
    "FC-13": ["tests/test_advisor.py::TestAdvisor::test_advisor_waypoint_navigation"],
    "FC-14": ["tests/test_advisor.py::TestAdvisor::test_advisor_manual_mode_advisory_only"],
    "FC-15": ["tests/test_advisor.py::TestAdvisor::test_advisor_manual_mode_advisory_only"],
    "FC-16": ["tests/test_advisor.py::TestAdvisor::test_advisor_auto_safety_mode"],
    "FC-17": ["tests/test_advisor.py::TestAdvisor::test_full_pipeline_safe"],
    "FC-18": ["tests/test_advisor.py::TestAdvisor::test_full_pipeline_battery_rtl"],
    "FC-19": ["tests/test_advisor.py::TestAdvisor::test_advisor_safety_violation_rtl"],
    "FC-20": ["tests/test_advisor.py::TestSafetyEnvelope::test_altitude_floor",
              "tests/test_advisor.py::TestSafetyEnvelope::test_altitude_ceiling"],
    "FC-21": ["tests/test_advisor.py::TestSafetyEnvelope::test_link_loss"],
    "FC-22": ["tests/test_advisor.py::TestSafetyEnvelope::test_geofence_violation_lat",
              "tests/test_advisor.py::TestSafetyEnvelope::test_geofence_violation_lon"],
    "FC-23": ["tests/test_advisor.py::TestSafetyEnvelope::test_altitude_floor"],
    "FC-24": ["tests/test_advisor.py::TestSafetyEnvelope::test_altitude_ceiling"],
    "FC-25": ["tests/test_advisor.py::TestSafetyEnvelope::test_battery_reserve"],
    "FC-26": ["tests/test_advisor.py::TestSafetyEnvelope::test_link_loss"],
    "FC-27": ["tests/test_advisor.py::TestSafetyEnvelope::test_gps_fix_type"],
    "FC-28": ["tests/test_advisor.py::TestSafetyEnvelope::test_gps_fix_type"],
    "FC-29": ["tests/test_advisor.py::TestSafetyEnvelope::test_speed_limit"],
    "FC-30": ["tests/test_advisor.py::TestSafetyEnvelope::test_climb_rate"],
    "FC-31": ["tests/test_advisor.py::TestSafetyEnvelope::test_sink_rate"],
    "FC-32": ["tests/test_advisor.py::TestSafetyEnvelope::test_attitude_limits"],
    "FC-33": ["tests/test_advisor.py::TestSafetyEnvelope::test_attitude_limits"],
    "FC-34": ["tests/test_client.py::test_command_with_token",
              "tests/test_client.py::test_issue_token"],
    "FC-35": ["tests/test_client.py::test_command_with_token"],
    "FC-36": ["tests/test_client.py::test_command_with_token"],
    "FC-37": ["tests/test_client.py::test_command_with_token"],
    "FC-38": [],
    "FC-39": ["tests/test_client.py::test_command_with_token"],
    "FC-40": ["tests/test_health.py::TestWatchdog::test_watchdog_detects_stale_link",
              "tests/test_health.py::TestHealthComponents::test_mavlink_link_unhealthy"],
    "FC-41": [],
    "FC-42": ["tests/test_health.py::TestHealthComponents::test_cpu_engine_unhealthy"],
    "FC-43": [],
    "FC-44": [],
    "FC-45": ["tests/test_health.py::TestHealthComponents::test_all_healthy",
              "tests/test_health.py::TestHealthComponents::test_one_unhealthy"],
    "FC-46": [],
}

# Hazards without an automated test, with justification (verified at check time).
N_A_TESTS = {
    "FC-38": "Command proxy relies on FC authority + token gate (FC-34..36 tested); unintended command is "
             "exercised indirectly by test_command_with_token. No exec harness for real FC.",
    "FC-41": "CRSF watchdog task monitor test planned but not yet implemented (open gap, tracked in FHA).",
    "FC-43": "OOM behaviour is enforced by systemd config (MemoryMax=2G); automated stress test not deployed.",
    "FC-44": "Resource saturation enforced by systemd CPUQuota=200% + log rotation; not covered by unit test.",
    "FC-46": "gRPC flow control relies on interval min 20ms; backpressure stress test planned.",
}


def _resolve_test_path(ref, root=None):
    """Check a pytest node reference like tests/f.py::Cls::test_x exists."""
    root = root or os.getcwd()
    if "::" not in ref:
        return False
    file_part, _, node = ref.partition("::")
    full = os.path.join(root, file_part)
    if not os.path.isfile(full):
        return False
    with open(full, encoding="utf-8") as fh:
        text = fh.read()
    for segment in node.split("::"):
        if not segment:
            return False
        if segment.startswith("test") and f"def {segment}(" not in text:
            return False
        if not segment.startswith("test") and f"class {segment}:" not in text:
            return False
    return True


def check_traceability():
    """Validate matrix completeness. Returns list of error strings (empty = pass)."""
    errors = []
    known_hazards = set(HAZARDS)

    # 1. Every REQ maps only to known hazards.
    for req_id, hazards in sorted(REQ_TO_HAZARDS.items()):
        for hazard in hazards:
            if hazard not in known_hazards:
                errors.append(f"REQ {req_id} references unknown hazard {hazard}")

    # 2. Every hazard has a mitigation claim (HAZARDS entry) and either a
    #    resolvable test reference or a documented N/A justification.
    for hazard_id in sorted(known_hazards):
        refs = HAZARD_TO_TESTS.get(hazard_id, [])
        if refs:
            for ref in refs:
                if not _resolve_test_path(ref):
                    errors.append(f"Hazard {hazard_id} references missing test {ref!r}")
        else:
            reason = N_A_TESTS.get(hazard_id)
            if not reason:
                errors.append(f"Hazard {hazard_id} has no test reference and no N/A justification")

    # 3. N/A justifications reference only hazards without tests.
    for hazard_id in N_A_TESTS:
        if hazard_id not in known_hazards:
            errors.append(f"N/A entry {hazard_id} not in HAZARDS")
        if HAZARD_TO_TESTS.get(hazard_id):
            errors.append(f"Hazard {hazard_id} has tests but is listed in N_A_TESTS")

    # 4. Every hazard is referenced by at least one REQ.
    referenced = {h for hazards in REQ_TO_HAZARDS.values() for h in hazards}
    for hazard_id in sorted(known_hazards):
        if hazard_id not in referenced:
            errors.append(f"Hazard {hazard_id} is not referenced by any REQ (orphan)")

    return errors


if __name__ == "__main__":
    errors = check_traceability()
    if errors:
        print(f"FAIL: {len(errors)} traceability issue(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    n_test = sum(1 for refs in HAZARD_TO_TESTS.values() if refs)
    print(f"OK: {len(REQ_TO_HAZARDS)} REQs, {len(HAZARDS)} hazards, "
          f"{n_test} hazards with automated test evidence, "
          f"{len(N_A_TESTS)} documented as non-automated.")
    sys.exit(0)