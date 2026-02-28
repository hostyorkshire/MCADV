"""
Test utilities – factories and helpers shared across test modules.
"""

import os
import sys
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import AdventureBot  # noqa: E402
from meshcore import MeshCoreMessage  # noqa: E402


class MessageFactory:
    """Creates MeshCoreMessage instances with sensible defaults."""

    @classmethod
    def create(
        cls,
        sender: str = "TestUser",
        content: str = "!adv",
        channel_idx: int = 1,
        message_type: str = "text",
    ) -> MeshCoreMessage:
        return MeshCoreMessage(
            sender=sender,
            content=content,
            channel_idx=channel_idx,
            message_type=message_type,
        )


class SessionFactory:
    """Creates session dicts with sensible defaults."""

    @classmethod
    def create(
        cls,
        status: str = "active",
        theme: str = "fantasy",
        node: str = "start",
        history=None,
    ) -> dict:
        return {
            "status": status,
            "theme": theme,
            "node": node,
            "history": history if history is not None else [],
            "last_active": time.time(),
        }


class BotFactory:
    """Creates AdventureBot instances suitable for unit testing."""

    @classmethod
    def create(cls, **kwargs) -> AdventureBot:
        defaults = dict(
            debug=False,
            ollama_url="http://localhost:11434",
            model="test-model",
            http_host="0.0.0.0",
            http_port=5000,
        )
        defaults.update(kwargs)
        bot = AdventureBot(**defaults)
        bot._sessions = {}
        bot._save_sessions = MagicMock()
        bot._call_ollama = MagicMock(return_value=None)
        return bot


# ---------------------------------------------------------------------------
# Standalone helper functions
# ---------------------------------------------------------------------------


def make_test_message(
    sender: str = "TestUser",
    content: str = "!adv",
    channel_idx: int = 1,
) -> MeshCoreMessage:
    """Convenience wrapper around MessageFactory.create()."""
    return MessageFactory.create(sender=sender, content=content, channel_idx=channel_idx)


def make_active_session(theme: str = "fantasy") -> dict:
    """Return an active session dict ready for insertion into bot._sessions."""
    return SessionFactory.create(theme=theme)
