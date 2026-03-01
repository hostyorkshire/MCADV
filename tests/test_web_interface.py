#!/usr/bin/env python3
"""
Tests for the MCADV web interface API endpoints.

Tests all new /api/adventure/* and /api/themes endpoints, session management,
error handling, and isolation from mesh sessions.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import AdventureBot, VALID_THEMES, _is_valid_uuid  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_UUID = "12345678-1234-4678-9234-567812345678"


def make_bot(**kwargs) -> AdventureBot:
    """Create an AdventureBot for testing with no disk I/O."""
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
# UUID helper
# ---------------------------------------------------------------------------


class TestIsValidUUID(unittest.TestCase):
    def test_valid_uuid(self):
        self.assertTrue(_is_valid_uuid(VALID_UUID))

    def test_invalid_empty(self):
        self.assertFalse(_is_valid_uuid(""))

    def test_invalid_short(self):
        self.assertFalse(_is_valid_uuid("not-a-uuid"))

    def test_valid_uppercase(self):
        self.assertTrue(_is_valid_uuid(VALID_UUID.upper()))


# ---------------------------------------------------------------------------
# Session key helpers
# ---------------------------------------------------------------------------


class TestWebSessionKey(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_web_session_key_format(self):
        key = self.bot._session_key_web(VALID_UUID)
        self.assertEqual(key, f"web_{VALID_UUID}")

    def test_is_web_session_true(self):
        key = self.bot._session_key_web(VALID_UUID)
        self.assertTrue(self.bot._is_web_session(key))

    def test_is_web_session_false_for_channel(self):
        self.assertFalse(self.bot._is_web_session("channel_1"))

    def test_web_and_mesh_keys_do_not_conflict(self):
        web_key = self.bot._session_key_web(VALID_UUID)
        mesh_key = "channel_1"
        self.assertNotEqual(web_key, mesh_key)


# ---------------------------------------------------------------------------
# /api/themes endpoint
# ---------------------------------------------------------------------------


class TestThemesEndpoint(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()

    def test_returns_200(self):
        resp = self.client.get("/api/themes")
        self.assertEqual(resp.status_code, 200)

    def test_returns_all_themes(self):
        resp = self.client.get("/api/themes")
        data = resp.get_json()
        self.assertIn("themes", data)
        self.assertEqual(set(data["themes"]), set(VALID_THEMES))


# ---------------------------------------------------------------------------
# /api/health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()

    def test_health_returns_mode(self):
        resp = self.client.get("/api/health")
        data = resp.get_json()
        self.assertIn("mode", data)
        self.assertEqual(data["mode"], "http")

    def test_distributed_mode_reported(self):
        bot = make_bot(distributed_mode=True)
        client = bot.app.test_client()
        data = client.get("/api/health").get_json()
        self.assertEqual(data["mode"], "distributed")


# ---------------------------------------------------------------------------
# POST /api/adventure/start
# ---------------------------------------------------------------------------


class TestAdventureStart(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()

    def _start(self, payload):
        return self.client.post(
            "/api/adventure/start",
            json=payload,
            content_type="application/json",
        )

    def test_start_default_theme(self):
        resp = self._start({})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("session_id", data)
        self.assertIn("story", data)
        self.assertIn("choices", data)
        self.assertEqual(data["status"], "active")

    def test_start_explicit_theme(self):
        resp = self._start({"theme": "scifi"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "active")

    def test_start_invalid_theme_returns_400(self):
        resp = self._start({"theme": "unicorns"})
        self.assertEqual(resp.status_code, 400)

    def test_start_custom_session_id(self):
        resp = self._start({"session_id": VALID_UUID})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["session_id"], VALID_UUID)

    def test_start_invalid_session_id_returns_400(self):
        resp = self._start({"session_id": "not-a-uuid"})
        self.assertEqual(resp.status_code, 400)

    def test_start_creates_web_session(self):
        resp = self._start({"session_id": VALID_UUID})
        self.assertEqual(resp.status_code, 200)
        session = self.bot._get_session(f"web_{VALID_UUID}")
        self.assertEqual(session.get("status"), "active")

    def test_start_does_not_create_mesh_session(self):
        resp = self._start({"session_id": VALID_UUID})
        self.assertEqual(resp.status_code, 200)
        # Channel session should not exist
        self.assertEqual(self.bot._get_session("channel_1"), {})

    def test_start_story_has_choices(self):
        resp = self._start({"theme": "fantasy"})
        data = resp.get_json()
        # fantasy start node has 3 choices
        self.assertEqual(len(data["choices"]), 3)


# ---------------------------------------------------------------------------
# POST /api/adventure/choice
# ---------------------------------------------------------------------------


class TestAdventureChoice(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()
        # Pre-create an active session
        self.bot._update_session(
            f"web_{VALID_UUID}",
            {"status": "active", "theme": "fantasy", "node": "start", "history": []},
        )

    def _choice(self, payload):
        return self.client.post(
            "/api/adventure/choice",
            json=payload,
            content_type="application/json",
        )

    def test_valid_choice_returns_200(self):
        resp = self._choice({"session_id": VALID_UUID, "choice": "1"})
        self.assertEqual(resp.status_code, 200)

    def test_choice_returns_story_and_choices(self):
        resp = self._choice({"session_id": VALID_UUID, "choice": "1"})
        data = resp.get_json()
        self.assertIn("story", data)
        self.assertIn("choices", data)
        self.assertIn("status", data)

    def test_invalid_choice_returns_400(self):
        resp = self._choice({"session_id": VALID_UUID, "choice": "9"})
        self.assertEqual(resp.status_code, 400)

    def test_missing_session_id_returns_400(self):
        resp = self._choice({"choice": "1"})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_session_id_returns_400(self):
        resp = self._choice({"session_id": "not-uuid", "choice": "1"})
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_session_returns_404(self):
        resp = self._choice(
            {"session_id": "00000000-0000-0000-0000-000000000000", "choice": "1"}
        )
        self.assertEqual(resp.status_code, 404)

    def test_finished_adventure_clears_session(self):
        # Use a node that leads to a terminal node when choice "1" is made
        self.bot._update_session(
            f"web_{VALID_UUID}",
            {"status": "active", "theme": "fantasy", "node": "road", "history": []},
        )
        resp = self._choice({"session_id": VALID_UUID, "choice": "1"})
        data = resp.get_json()
        self.assertEqual(data["status"], "finished")
        # Session should be cleared after finishing
        self.assertEqual(self.bot._get_session(f"web_{VALID_UUID}"), {})


# ---------------------------------------------------------------------------
# GET /api/adventure/status
# ---------------------------------------------------------------------------


class TestAdventureStatus(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()

    def test_active_session_returns_status(self):
        self.bot._update_session(
            f"web_{VALID_UUID}",
            {"status": "active", "theme": "fantasy", "node": "start", "history": []},
        )
        resp = self.client.get(f"/api/adventure/status?session_id={VALID_UUID}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["theme"], "fantasy")

    def test_nonexistent_session_returns_none(self):
        resp = self.client.get(f"/api/adventure/status?session_id={VALID_UUID}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "none")

    def test_missing_session_id_returns_400(self):
        resp = self.client.get("/api/adventure/status")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_session_id_returns_400(self):
        resp = self.client.get("/api/adventure/status?session_id=bad-id")
        self.assertEqual(resp.status_code, 400)

    def test_history_length_reported(self):
        self.bot._update_session(
            f"web_{VALID_UUID}",
            {"status": "active", "theme": "fantasy", "node": "start", "history": ["a", "b"]},
        )
        resp = self.client.get(f"/api/adventure/status?session_id={VALID_UUID}")
        data = resp.get_json()
        self.assertEqual(data["history_length"], 2)


# ---------------------------------------------------------------------------
# POST /api/adventure/quit
# ---------------------------------------------------------------------------


class TestAdventureQuit(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()
        self.bot._update_session(
            f"web_{VALID_UUID}",
            {"status": "active", "theme": "fantasy", "node": "start", "history": []},
        )

    def _quit(self, payload):
        return self.client.post(
            "/api/adventure/quit",
            json=payload,
            content_type="application/json",
        )

    def test_quit_returns_200(self):
        resp = self._quit({"session_id": VALID_UUID})
        self.assertEqual(resp.status_code, 200)

    def test_quit_clears_session(self):
        self._quit({"session_id": VALID_UUID})
        self.assertEqual(self.bot._get_session(f"web_{VALID_UUID}"), {})

    def test_quit_returns_quit_status(self):
        data = self._quit({"session_id": VALID_UUID}).get_json()
        self.assertEqual(data["status"], "quit")

    def test_quit_missing_session_id_returns_400(self):
        resp = self._quit({})
        self.assertEqual(resp.status_code, 400)

    def test_quit_invalid_session_id_returns_400(self):
        resp = self._quit({"session_id": "not-uuid"})
        self.assertEqual(resp.status_code, 400)

    def test_quit_nonexistent_session_is_safe(self):
        # Quitting a session that doesn't exist should still succeed
        resp = self._quit({"session_id": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Session isolation: web sessions vs mesh sessions
# ---------------------------------------------------------------------------


class TestSessionIsolation(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()

    def test_web_and_mesh_sessions_isolated(self):
        """Web sessions must not interfere with mesh channel sessions."""
        # Start a mesh session on channel 1
        self.bot._update_session("channel_1", {"status": "active", "theme": "scifi"})

        # Start a web session
        resp = self.client.post(
            "/api/adventure/start",
            json={"session_id": VALID_UUID, "theme": "fantasy"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        # Mesh session should be untouched
        mesh_session = self.bot._get_session("channel_1")
        self.assertEqual(mesh_session.get("theme"), "scifi")
        self.assertEqual(mesh_session.get("status"), "active")

    def test_quit_web_session_does_not_affect_mesh(self):
        self.bot._update_session("channel_1", {"status": "active", "theme": "horror"})
        self.bot._update_session(f"web_{VALID_UUID}", {"status": "active", "theme": "fantasy"})

        self.client.post(
            "/api/adventure/quit",
            json={"session_id": VALID_UUID},
            content_type="application/json",
        )

        mesh_session = self.bot._get_session("channel_1")
        self.assertEqual(mesh_session.get("status"), "active")


# ---------------------------------------------------------------------------
# Multiple concurrent web sessions
# ---------------------------------------------------------------------------

UUID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
UUID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class TestConcurrentWebSessions(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.client = self.bot.app.test_client()

    def _start(self, session_id, theme="fantasy"):
        return self.client.post(
            "/api/adventure/start",
            json={"session_id": session_id, "theme": theme},
            content_type="application/json",
        )

    def test_two_web_sessions_independent(self):
        self._start(UUID_A, theme="fantasy")
        self._start(UUID_B, theme="scifi")

        session_a = self.bot._get_session(f"web_{UUID_A}")
        session_b = self.bot._get_session(f"web_{UUID_B}")

        self.assertEqual(session_a.get("theme"), "fantasy")
        self.assertEqual(session_b.get("theme"), "scifi")

    def test_choice_on_session_a_does_not_affect_b(self):
        self._start(UUID_A, theme="fantasy")
        self._start(UUID_B, theme="fantasy")

        node_b_before = self.bot._get_session(f"web_{UUID_B}").get("node")

        self.client.post(
            "/api/adventure/choice",
            json={"session_id": UUID_A, "choice": "2"},
            content_type="application/json",
        )

        node_b_after = self.bot._get_session(f"web_{UUID_B}").get("node")
        self.assertEqual(node_b_before, node_b_after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
