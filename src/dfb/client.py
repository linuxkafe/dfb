"""Typed client for Deck Fly Brain service."""
import os
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import requests
import numpy as np


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


class DeckClient:
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

    def _post(self, path: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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


def create_client_from_env() -> DeckClient:
    """Create client using DFB_HOST/DFB_PORT env vars."""
    host = os.getenv("DFB_HOST", "steamdeck")
    port = int(os.getenv("DFB_PORT", "8082"))
    return DeckClient(host=host, port=port)