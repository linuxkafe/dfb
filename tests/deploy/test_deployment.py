"""Offline integration tests for the Deck deployment surface.

These tests validate the deployment artifacts (systemd unit, deploy script,
port/env consistency) and prove the deployed app boots — all WITHOUT Steam Deck
hardware. They prepare for Sprint 03 hardware validation (T010/T011).
"""

import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy"
SYSTEMD_UNIT = DEPLOY_DIR / "flybrain.service"
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy_deck.sh"
SERVICE_MODULE = REPO_ROOT / "src" / "dfb" / "service.py"
DECK_TEST = REPO_ROOT / "tests" / "deck" / "test_integration.py"

EXPECTED_HTTP_PORT = "8082"
EXPECTED_GRPC_PORT = "8083"


# --------------------------------------------------------------------------
# systemd unit structural validation
# --------------------------------------------------------------------------
def _unit_section(lines: List[str], section: str) -> List[str]:
    result = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = stripped == f"[{section}]"
            continue
        if in_section and stripped and not stripped.startswith("#"):
            result.append(stripped)
    return result


def _read_unit() -> Dict[str, str]:
    text = SYSTEMD_UNIT.read_text()
    pairs: Dict[str, List[str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            pairs.setdefault(key, []).append(value)
    folded = {k: " ".join(v) for k, v in pairs.items()}
    # Expand Environment=KEY=VAL entries into top-level KEY->VAL pairs so
    # individual env vars can be asserted on directly.
    for directive in folded.get("Environment", "").split():
        if "=" in directive:
            k, _, v = directive.partition("=")
            folded.setdefault(k, v)
    return folded


class TestSystemdUnit:
    def test_unit_file_exists(self):
        assert SYSTEMD_UNIT.is_file(), "deploy/flybrain.service missing"

    def test_unit_is_valid_simple(self):
        lines = SYSTEMD_UNIT.read_text().splitlines()
        assert _unit_section(lines, "Unit"), "missing [Unit] section"
        assert _unit_section(lines, "Service"), "missing [Service] section"
        assert _unit_section(lines, "Install"), "missing [Install] section"
        assert "WantedBy=default.target" in _unit_section(lines, "Install")

    def test_execstart_uses_uvicorn_app(self):
        pairs = _read_unit()
        exec_start = pairs.get("ExecStart", "")
        assert "uvicorn" in exec_start, f"ExecStart missing uvicorn: {exec_start}"
        assert "dfb.service:app" in exec_start, (
            f"ExecStart must target dfb.service:app, got: {exec_start}"
        )

    def test_execstart_module_app_exists(self):
        pairs = _read_unit()
        exec_start = pairs["ExecStart"]
        match = re.search(r"(\S+\.service):(\w+)", exec_start)
        assert match, "cannot parse module:attr from ExecStart"
        module_path, attr = match.groups()
        # src/dfb/service.py -> module dotted path src.dfb.service
        service_py = REPO_ROOT / "src" / f"{module_path.replace('.', '/')}.py"
        assert service_py.is_file(), f"module file missing: {service_py}"
        # attr must exist in module
        sys.path.insert(0, str(REPO_ROOT / "src"))
        try:
            import importlib

            mod = importlib.import_module(module_path)
            assert hasattr(mod, attr), f"{module_path} has no attribute '{attr}'"
        finally:
            sys.path.pop(0)

    def test_http_port_matches_contract(self):
        pairs = _read_unit()
        exec_start = pairs["ExecStart"]
        assert f"--port {EXPECTED_HTTP_PORT}" in exec_start, (
            f"systemd unit HTTP port must be {EXPECTED_HTTP_PORT}, got: {exec_start}"
        )

    def test_mavlink_env_present(self):
        pairs = _read_unit()
        assert "MAVLINK_DEVICE" in pairs, "MAVLINK_DEVICE not set in unit"
        assert "MAVLINK_BAUD" in pairs, "MAVLINK_BAUD not set in unit"
        assert pairs["MAVLINK_DEVICE"].startswith("/dev/ttyACM")

    def test_crsf_env_present(self):
        pairs = _read_unit()
        assert "CRSF_DEVICE" in pairs, "CRSF_DEVICE not set in unit"
        assert "CRSF_BAUD" in pairs, "CRSF_BAUD not set in unit"

    def test_resource_limits_for_deck_hardware(self):
        pairs = _read_unit()
        assert "MemoryMax" in pairs, "MemoryMax limit missing"
        assert "CPUQuota" in pairs, "CPUQuota limit missing"

    def test_sleep_inhibit_guard_present(self):
        """Safety-relevant: service must prevent Deck from sleeping mid-flight.

        The inhibitor must WRAP the ExecStart command (lock held for the
        service's lifetime). A bare `systemd-inhibit` without a command
        (e.g. as ExecStartPre) spawns an interactive shell and never provides
        the guarantee — assert the semantics, not just the string.
        """
        pairs = _read_unit()
        exec_start = pairs.get("ExecStart", "")
        assert "systemd-inhibit" in exec_start, (
            "ExecStart must run uvicorn under systemd-inhibit"
        )
        assert "--what=sleep:handle-lid-switch" in exec_start, (
            "inhibitor must block sleep and lid close"
        )
        assert "--mode=block" in exec_start, "inhibitor must block, not delay"
        assert "--" in exec_start, "inhibitor must wrap a COMMAND via '--'"
        assert "uvicorn" in exec_start, (
            f"uvicorn must be the inhibited command, got: {exec_start}"
        )
        lines = SYSTEMD_UNIT.read_text()
        assert "ExecStartPre" not in lines, (
            "inhibitor must live in ExecStart, not ExecStartPre "
            "(a no-command ExecStartPre never holds the lock for the service)"
        )

    def test_restart_policy(self):
        pairs = _read_unit()
        assert pairs.get("Restart") == "on-failure"
        assert pairs.get("RestartSec") == "5"


# --------------------------------------------------------------------------
# port / env consistency across all deployment artifacts
# --------------------------------------------------------------------------
class TestDeploymentConsistency:
    def test_service_py_default_http_port(self):
        text = SERVICE_MODULE.read_text()
        assert EXPECTED_HTTP_PORT in text, "service.py default HTTP port drift"
        assert "uvicorn" in text

    def test_service_py_grpc_port_env(self):
        text = SERVICE_MODULE.read_text()
        assert "GRPC_PORT" in text
        assert EXPECTED_GRPC_PORT in text

    def test_deploy_script_port_matches(self):
        text = DEPLOY_SCRIPT.read_text()
        assert f"SERVICE_PORT={EXPECTED_HTTP_PORT}" in text

    def test_deploy_script_host(self):
        text = DEPLOY_SCRIPT.read_text()
        assert "deck@steamdeck" in text

    def test_makefile_test_deck_port_matches(self):
        makefile = (REPO_ROOT / "Makefile").read_text()
        assert EXPECTED_HTTP_PORT in makefile

    def test_deck_integration_default_port_matches(self):
        text = DECK_TEST.read_text()
        assert EXPECTED_HTTP_PORT in text

    def test_deck_integration_lan_host(self):
        text = DECK_TEST.read_text()
        assert "steamdeck" in text


# --------------------------------------------------------------------------
# deploy script integrity
# --------------------------------------------------------------------------
class TestDeployScriptIntegrity:
    def test_script_exists_and_executable(self):
        assert DEPLOY_SCRIPT.is_file(), "scripts/deploy_deck.sh missing"
        assert os.access(DEPLOY_SCRIPT, os.X_OK), "deploy_deck.sh not executable"

    def test_script_sources(self):
        text = DEPLOY_SCRIPT.read_text()
        for rel in [
            "src/",
            "sim/",
            "shaders/",
            "pyproject.toml",
            "Makefile",
            "deploy/flybrain.service",
        ]:
            assert rel in text, f"deploy script does not sync {rel}"

    def test_synced_paths_exist(self):
        assert (REPO_ROOT / "src").is_dir()
        assert (REPO_ROOT / "sim").is_dir()
        assert (REPO_ROOT / "shaders").is_dir()
        assert (REPO_ROOT / "pyproject.toml").is_file()

    def test_script_creates_venv_and_deps(self):
        text = DEPLOY_SCRIPT.read_text()
        assert "python3 -m venv" in text
        assert "pip install" in text

    def test_script_installs_systemd_unit(self):
        text = DEPLOY_SCRIPT.read_text()
        assert "flybrain.service" in text
        assert "systemctl --user" in text
        assert "daemon-reload" in text

    def test_script_warns_about_group_dialout(self):
        text = DEPLOY_SCRIPT.read_text()
        assert "dialout" in text, "serial port permission check missing"


# --------------------------------------------------------------------------
# smoke boot: prove the deployed command actually boots and serves
# --------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestSmokeBoot:
    @pytest.mark.integration
    def test_uvicorn_boots_and_serves_health(self):
        """Spawn uvicorn exactly like the systemd unit, hit /health + /version."""
        if not shutil.which("uvicorn"):
            pytest.skip("uvicorn not on PATH")
        http_port = _free_port()
        grpc_port = _free_port()
        env = os.environ.copy()
        env.update(
            {
                "TELEMETRY_PROTOCOL": "none",
                "GRPC_PORT": str(grpc_port),
                "PYTHONUNBUFFERED": "1",
            }
        )
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.dfb.service:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(http_port),
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            health_url = f"http://127.0.0.1:{http_port}/health"
            last_err = None
            data = None
            resp_status = None
            for _ in range(40):
                if proc.poll() is not None:
                    output = proc.stdout.read().decode() if proc.stdout else ""
                    raise AssertionError(
                        f"uvicorn exited early ({proc.returncode})\n{output}"
                    )
                try:
                    with urllib.request.urlopen(health_url, timeout=1) as resp:
                        resp_status = resp.status
                        data = resp.read().decode()
                        break
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    time.sleep(0.25)
            else:
                raise AssertionError(f"service never became reachable: {last_err}")

            # Process exited before boot completed — report real output.
            if proc.poll() is not None:
                output = proc.stdout.read().decode() if proc.stdout else ""
                raise AssertionError(
                    f"uvicorn exited before serving (code {proc.returncode})\n{output}"
                )

            # Content assertions must not be masked by the retry loop above.
            assert resp_status == 200, f"unexpected /health status {resp_status}"
            assert '"components"' in data, f"missing components in: {data}"
            assert '"status"' in data, f"missing status in: {data}"
            # Without telemetry connected, status is "unhealthy" by design —
            # the endpoint must still serve valid JSON.
            assert any(s in data for s in ('"unhealthy"', '"ok"')), (
                f"unexpected status payload: {data}"
            )

            with urllib.request.urlopen(
                f"http://127.0.0.1:{http_port}/version", timeout=2
            ) as resp:
                assert resp.status == 200
                version = resp.read().decode()
                assert "version" in version
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
