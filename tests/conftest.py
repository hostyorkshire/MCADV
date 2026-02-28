"""
pytest fixtures shared across all test modules.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import AdventureBot  # noqa: E402
from meshcore import MeshCoreMessage  # noqa: E402


@pytest.fixture()
def bot():
    """Return an AdventureBot with empty in-memory sessions and no disk I/O."""
    instance = AdventureBot(
        debug=False,
        ollama_url="http://localhost:11434",
        model="test-model",
        http_host="0.0.0.0",
        http_port=5000,
    )
    instance._sessions = {}
    instance._save_sessions = MagicMock()
    instance._call_ollama = MagicMock(return_value=None)
    return instance


@pytest.fixture()
def make_msg():
    """Return a factory function for MeshCoreMessage objects."""

    def _factory(sender="Alice", content="!adv", channel_idx=1):
        return MeshCoreMessage(sender=sender, content=content, channel_idx=channel_idx)

    return _factory


@pytest.fixture()
def temp_dir():
    """Yield a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def mock_ollama(bot):
    """Patch _call_ollama to always return None (forces fallback stories)."""
    bot._call_ollama = MagicMock(return_value=None)
    return bot


@pytest.fixture()
def sample_session():
    """Return a typical active session dict."""
    return {
        "status": "active",
        "theme": "fantasy",
        "node": "start",
        "history": [],
    }
