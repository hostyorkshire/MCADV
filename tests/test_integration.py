"""
End-to-end / integration tests for MCADV.

All serial and HTTP I/O is mocked so no hardware or running server is required.
"""

import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import AdventureBot  # noqa: E402
from meshcore import MeshCoreMessage  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bot(**kwargs) -> AdventureBot:
    defaults = dict(
        debug=False,
        ollama_url="http://localhost:11434",
        model="test-model",
        http_host="127.0.0.1",
        http_port=5000,
    )
    defaults.update(kwargs)
    bot = AdventureBot(**defaults)
    bot._sessions = {}
    bot._save_sessions = MagicMock()
    bot._call_ollama = MagicMock(return_value=None)
    return bot


def _msg(sender="Alice", content="!adv", channel_idx=1) -> MeshCoreMessage:
    return MeshCoreMessage(sender=sender, content=content, channel_idx=channel_idx)


# =============================================================================
# TestDistributedMode – full message round-trip without hardware
# =============================================================================


class TestDistributedMode(unittest.TestCase):
    """Full workflow test: message in → response out, no real network."""

    def setUp(self):
        self.bot = _make_bot()

    def test_start_adventure_returns_response(self):
        reply = self.bot.handle_message(_msg(content="!adv fantasy"))
        self.assertIsNotNone(reply)
        self.assertIsInstance(reply, str)

    def test_choice_after_start_returns_response(self):
        self.bot.handle_message(_msg(content="!adv"))
        reply = self.bot.handle_message(_msg(content="1"))
        self.assertIsNotNone(reply)

    def test_help_returns_command_list(self):
        reply = self.bot.handle_message(_msg(content="!help"))
        self.assertIn("!adv", reply)

    def test_status_after_start(self):
        self.bot.handle_message(_msg(content="!adv scifi"))
        reply = self.bot.handle_message(_msg(content="!status"))
        self.assertIn("scifi", reply)

    def test_quit_ends_adventure(self):
        self.bot.handle_message(_msg(content="!adv"))
        reply = self.bot.handle_message(_msg(content="!quit"))
        self.assertIn("!adv", reply)

    def test_unknown_message_returns_none(self):
        reply = self.bot.handle_message(_msg(content="just chatting"))
        self.assertIsNone(reply)

    def test_session_persists_across_multiple_messages(self):
        self.bot.handle_message(_msg(content="!adv horror"))
        self.bot.handle_message(_msg(content="1"))
        key = "channel_1"
        session = self.bot._get_session(key)
        # Session may have been cleared if terminal node reached, that's OK
        if session:
            self.assertEqual(session.get("theme"), "horror")

    def test_flask_health_endpoint(self):
        with self.bot.app.test_client() as client:
            resp = client.get("/api/health")
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertEqual(data["status"], "healthy")

    def test_flask_message_endpoint(self):
        with self.bot.app.test_client() as client:
            payload = {"sender": "Alice", "content": "!adv", "channel_idx": 1}
            resp = client.post(
                "/api/message",
                json=payload,
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertIn("response", data)

    def test_flask_message_endpoint_with_help(self):
        with self.bot.app.test_client() as client:
            payload = {"sender": "Alice", "content": "!help", "channel_idx": 1}
            resp = client.post("/api/message", json=payload)
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertIn("!adv", data.get("response", ""))


# =============================================================================
# TestGatewayBotCommunication
# =============================================================================


class TestGatewayBotCommunication(unittest.TestCase):
    """Simulate gateway → bot server HTTP communication using Flask test client."""

    def setUp(self):
        self.bot = _make_bot()
        self.client = self.bot.app.test_client()

    def test_post_message_returns_json(self):
        resp = self.client.post(
            "/api/message",
            json={"sender": "GW", "content": "!adv", "channel_idx": 1},
        )
        self.assertEqual(resp.content_type, "application/json")

    def test_post_message_response_field_present(self):
        resp = self.client.post(
            "/api/message",
            json={"sender": "GW", "content": "!adv", "channel_idx": 1},
        )
        data = json.loads(resp.data)
        self.assertIn("response", data)

    def test_health_check_returns_healthy(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertEqual(data.get("status"), "healthy")

    def test_post_choice_after_start(self):
        self.client.post(
            "/api/message",
            json={"sender": "GW", "content": "!adv", "channel_idx": 1},
        )
        resp = self.client.post(
            "/api/message",
            json={"sender": "GW", "content": "2", "channel_idx": 1},
        )
        self.assertEqual(resp.status_code, 200)

    def test_different_channels_independent(self):
        self.client.post("/api/message", json={"sender": "GW", "content": "!adv fantasy", "channel_idx": 1})
        self.client.post("/api/message", json={"sender": "GW", "content": "!adv scifi", "channel_idx": 2})
        s1 = self.bot._get_session("channel_1")
        s2 = self.bot._get_session("channel_2")
        self.assertEqual(s1.get("theme"), "fantasy")
        self.assertEqual(s2.get("theme"), "scifi")


# =============================================================================
# TestSessionSynchronization
# =============================================================================


class TestSessionSynchronization(unittest.TestCase):
    """Test session state management under concurrent access."""

    def setUp(self):
        self.bot = _make_bot()

    def test_concurrent_updates_are_safe(self):
        errors = []

        def worker(i):
            try:
                self.bot._update_session(f"user_{i}", {"status": "active", "theme": "fantasy"})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_session_not_lost_under_concurrent_reads(self):
        self.bot._update_session("shared", {"status": "active", "theme": "horror"})
        results = []

        def reader():
            results.append(self.bot._get_session("shared"))

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for r in results:
            self.assertEqual(r.get("theme"), "horror")

    def test_expire_sessions_under_load(self):
        for i in range(50):
            self.bot._update_session(f"old_{i}", {"status": "active"})
            self.bot._sessions[f"old_{i}"]["last_active"] = 0.0  # instant expire
        self.bot._expire_sessions()
        for i in range(50):
            self.assertEqual(self.bot._get_session(f"old_{i}"), {})

    def test_update_and_clear_concurrent(self):
        errors = []

        def updater():
            for _ in range(10):
                self.bot._update_session("X", {"v": 1})

        def clearer():
            for _ in range(10):
                self.bot._clear_session("X")

        t1 = threading.Thread(target=updater)
        t2 = threading.Thread(target=clearer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(errors, [])


# =============================================================================
# TestMultiUserScenarios
# =============================================================================


class TestMultiUserScenarios(unittest.TestCase):
    """Multiple users interacting on the same and different channels."""

    def setUp(self):
        self.bot = _make_bot()

    def test_three_users_same_channel_share_session(self):
        for name in ("Alice", "Bob", "Carol"):
            self.bot.handle_message(_msg(sender=name, content="!adv fantasy", channel_idx=1))
        key = "channel_1"
        session = self.bot._get_session(key)
        self.assertEqual(session.get("theme"), "fantasy")

    def test_user_quit_affects_whole_channel(self):
        self.bot.handle_message(_msg(sender="Alice", content="!adv", channel_idx=1))
        self.bot.handle_message(_msg(sender="Bob", content="!quit", channel_idx=1))
        session = self.bot._get_session("channel_1")
        self.assertEqual(session, {})

    def test_five_channels_independent(self):
        for ch in range(1, 6):
            self.bot.handle_message(_msg(sender="U", content="!adv fantasy", channel_idx=ch))
        for ch in range(1, 6):
            s = self.bot._get_session(f"channel_{ch}")
            self.assertEqual(s.get("status"), "active")

    def test_help_does_not_affect_session(self):
        self.bot.handle_message(_msg(content="!adv horror", channel_idx=1))
        session_before = self.bot._get_session("channel_1").copy()
        self.bot.handle_message(_msg(content="!help", channel_idx=1))
        session_after = self.bot._get_session("channel_1")
        self.assertEqual(session_before.get("theme"), session_after.get("theme"))

    def test_status_does_not_affect_session(self):
        self.bot.handle_message(_msg(content="!adv scifi", channel_idx=1))
        node_before = self.bot._get_session("channel_1").get("node")
        self.bot.handle_message(_msg(content="!status", channel_idx=1))
        node_after = self.bot._get_session("channel_1").get("node")
        self.assertEqual(node_before, node_after)

    def test_sequential_choices_advance_story(self):
        self.bot.handle_message(_msg(content="!adv fantasy", channel_idx=1))
        node_start = self.bot._get_session("channel_1").get("node")
        self.bot.handle_message(_msg(content="1", channel_idx=1))
        session = self.bot._get_session("channel_1")
        # Either advanced or session cleared (terminal reached)
        if session:
            self.assertNotEqual(session.get("node"), node_start)


if __name__ == "__main__":
    unittest.main(verbosity=2)
