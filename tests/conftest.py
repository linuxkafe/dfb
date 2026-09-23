import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to Python path for tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_mavlink_message():
    """Create a mock MAVLink message with configurable type and fields."""

    def _make_msg(msg_type: str, **kwargs):
        msg = MagicMock()
        msg.get_type.return_value = msg_type
        for k, v in kwargs.items():
            setattr(msg, k, v)
        return msg

    return _make_msg


@pytest.fixture
def mock_mavlink_connection():
    """Create a mock MAVLink connection."""
    conn = MagicMock()
    conn.wait_heartbeat.return_value = None
    conn.recv_match.return_value = None
    conn.close.return_value = None
    return conn
