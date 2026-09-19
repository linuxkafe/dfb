"""Integration tests against deployed Fly Brain service on Steam Deck (direct LAN)."""
import os
import time
from typing import Any, Dict

import pytest
import requests

DECK_HOST = os.environ.get("DECK_HOST", "steamdeck")
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8082"))
BASE_URL = f"http://{DECK_HOST}:{SERVICE_PORT}"


class DeckClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 5.0):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def health(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def version(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/version", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def decide(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/decide", json=payload, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()


@pytest.fixture(scope="session")
def deck_client():
    """Client for Deck service (direct LAN access)."""
    client = DeckClient()
    # Verify service reachable
    for _ in range(10):
        try:
            client.health()
            break
        except requests.RequestException:
            time.sleep(0.5)
    else:
        pytest.fail(f"Cannot reach Deck service at {BASE_URL}")
    return client


class TestServiceHealth:
    def test_health_endpoint(self, deck_client):
        resp = deck_client.health()
        assert resp["status"] == "ok"
        assert "version" in resp

    def test_version_endpoint(self, deck_client):
        resp = deck_client.version()
        assert "version" in resp

    def test_decide_endpoint_exists(self, deck_client):
        payload = {
            "position": [0, 0],
            "grid": [[0] * 10 for _ in range(10)],
            "exit": [9, 9],
        }
        resp = deck_client.decide(payload)
        assert "action" in resp
        assert resp["action"] in ("UP", "DOWN", "LEFT", "RIGHT")
        assert "confidence" in resp
        assert 0 <= resp["confidence"] <= 1


class TestServiceLatency:
    def test_health_latency_p50(self, deck_client):
        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            deck_client.health()
            latencies.append((time.perf_counter() - start) * 1000)
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        assert p50 < 200, f"Health p50 latency {p50:.1f}ms exceeds 200ms"

    def test_decide_latency_p50(self, deck_client):
        payload = {
            "position": [0, 0],
            "grid": [[0] * 10 for _ in range(10)],
            "exit": [9, 9],
        }
        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            deck_client.decide(payload)
            latencies.append((time.perf_counter() - start) * 1000)
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        assert p50 < 500, f"Decide p50 latency {p50:.1f}ms exceeds 500ms"


class TestMazeBenchmark:
    @pytest.mark.slow
    def test_maze_episodes(self, deck_client):
        """Run maze benchmark episodes via service (direct LAN)."""
        from tests.maze_sim import run_benchmark

        results = run_benchmark(
            client=deck_client,
            episodes=20,  # Reduced for CI; full 100 in manual run
            size=10,
            obstacle_density=0.0,  # Empty maze so greedy matches optimal
            algorithm="bfs",
            seed=42,
        )

        # Basic assertions
        assert len(results) == 20
        success_rate = sum(1 for r in results if r.success) / len(results)
        assert success_rate > 0.5, f"Success rate {success_rate:.1%} too low"

        avg_latency = sum(r.latency_ms for r in results) / len(results)
        assert avg_latency < 1000, f"Avg latency {avg_latency:.1f}ms too high"

        # Print summary for manual inspection
        print("\nMaze Benchmark Summary (20 episodes, direct LAN):")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Avg latency: {avg_latency:.1f}ms")
        print(f"  Avg steps: {sum(r.steps for r in results) / len(results):.1f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
