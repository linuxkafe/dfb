"""Tests for DeckClient."""
from unittest.mock import Mock

import pytest

from src.dfb.client import DeckClient, create_client_from_env


@pytest.fixture
def mock_session():
    return Mock()


def test_health(mock_session):
    mock_resp = Mock()
    mock_resp.json.return_value = {"status": "ok", "version": "0.1.0"}
    mock_resp.raise_for_status.return_value = None
    mock_session.get.return_value = mock_resp

    client = DeckClient(session=mock_session)
    resp = client.health()
    assert resp.status == "ok"
    assert resp.version == "0.1.0"
    mock_session.get.assert_called_once_with(
        "http://steamdeck:8082/health", timeout=5.0
    )


def test_decide(mock_session):
    mock_resp = Mock()
    mock_resp.json.return_value = {
        "action": "UP",
        "confidence": 0.9,
        "logits": [0.1, 0.2, 0.3, 0.4],
    }
    mock_resp.raise_for_status.return_value = None
    mock_session.post.return_value = mock_resp

    client = DeckClient(session=Mock())
    client.session = mock_session
    resp = client.decide(position=[0, 0], grid=[[0]*10 for _ in range(10)], exit=[9, 9])
    assert resp.action == "UP"
    assert resp.confidence == 0.9
    assert resp.logits == [0.1, 0.2, 0.3, 0.4]


def test_issue_token(mock_session):
    mock_resp = Mock()
    mock_resp.json.return_value = {"token": "abc123", "expires_in": 30.0}
    mock_resp.raise_for_status.return_value = None
    mock_session.post.return_value = mock_resp

    client = DeckClient(session=mock_session)
    resp = client.issue_token()
    assert resp.token == "abc123"
    assert resp.expires_in == 30.0


def test_command_with_token():
    mock_session = Mock()
    mock_resp = Mock()
    mock_resp.json.return_value = {"success": True, "message": "OK"}
    mock_resp.raise_for_status.return_value = None
    mock_session.post.return_value = mock_resp

    client = DeckClient(session=mock_session)
    resp = client.command(action="ARM", token="token123")
    assert resp.success is True
    assert resp.message == "OK"
    # verify header passed
    called_kwargs = mock_session.post.call_args.kwargs
    assert called_kwargs["headers"]["X-Confirmation-Token"] == "token123"


def test_create_client_from_env(monkeypatch):
    monkeypatch.setenv("DFB_HOST", "myhost")
    monkeypatch.setenv("DFB_PORT", "9090")
    client = create_client_from_env()
    assert client.base_url == "http://myhost:9090"

