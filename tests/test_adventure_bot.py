#!/usr/bin/env python3
"""
Unit tests for MCADV Adventure Bot.

Tests the bot in distributed-only mode where handle_message() returns
response strings directly (no mesh object).
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import (  # noqa: E402
    FALLBACK_STORIES,
    STORY_RUNTIME_RESET_SECONDS,
    MAX_MSG_LEN,
    SESSION_EXPIRY_SECONDS,
    VALID_THEMES,
    AdventureBot,
    _FANTASY_STORY,
    _HORROR_STORY,
    _SCIFI_STORY,
)
from meshcore import MeshCoreMessage  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_bot(**kwargs) -> AdventureBot:
    """
    Create an AdventureBot for testing in distributed mode.

    The bot runs as an HTTP server and returns responses directly.
    Sessions are reset to an empty dict and _save_sessions is mocked
    so no disk I/O happens, preventing state from leaking between tests.
    """
    defaults = dict(
        debug=False,
        ollama_url="http://localhost:11434",
        model="test-model",
        http_host="0.0.0.0",
        http_port=5000,
    )
    defaults.update(kwargs)
    bot = AdventureBot(**defaults)
    # Isolate each test: start with clean in-memory sessions, no disk writes
    bot._sessions = {}
    bot._save_sessions = MagicMock()
    return bot


def make_msg(sender: str = "Alice", content: str = "!adv", channel_idx: int = 1) -> MeshCoreMessage:
    """
    Create a MeshCoreMessage for testing.

    In collaborative mode, all users on the same channel share the same story.
    The channel_idx determines which story session is used.
    """
    return MeshCoreMessage(sender=sender, content=content, channel_idx=channel_idx)


def get_session_key(channel_idx: int = 1) -> str:
    """
    Get the session key for a given channel in collaborative mode.

    Helper function for tests to get the correct session key based on channel.
    """
    return f"channel_{channel_idx}"


# ---------------------------------------------------------------------------
# Story message formatting
# ---------------------------------------------------------------------------


class TestFormatStoryMessage(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_with_three_choices(self):
        msg = self.bot._format_story_message("A dark cave.", ["Go in", "Turn back", "Shout"])
        self.assertIn("1:Go in", msg)
        self.assertIn("2:Turn back", msg)
        self.assertIn("3:Shout", msg)

    def test_terminal_node_returns_text_only(self):
        msg = self.bot._format_story_message("You win. THE END", [])
        self.assertEqual(msg, "You win. THE END")
        self.assertNotIn("1:", msg)

    def test_newline_separates_text_and_choices(self):
        msg = self.bot._format_story_message("A scene.", ["A", "B", "C"])
        self.assertIn("\n", msg)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


class TestSessionManagement(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_new_session_is_empty(self):
        self.assertEqual(self.bot._get_session("Bob"), {})

    def test_update_creates_session(self):
        self.bot._update_session("Alice", {"status": "active", "theme": "fantasy"})
        s = self.bot._get_session("Alice")
        self.assertEqual(s["status"], "active")
        self.assertEqual(s["theme"], "fantasy")
        self.assertIn("last_active", s)

    def test_update_merges_data(self):
        self.bot._update_session("Alice", {"theme": "fantasy"})
        self.bot._update_session("Alice", {"status": "active"})
        s = self.bot._get_session("Alice")
        self.assertEqual(s["theme"], "fantasy")
        self.assertEqual(s["status"], "active")

    def test_clear_removes_session(self):
        self.bot._update_session("Alice", {"status": "active"})
        self.bot._clear_session("Alice")
        self.assertEqual(self.bot._get_session("Alice"), {})

    def test_clear_nonexistent_session_is_safe(self):
        self.bot._clear_session("nobody")  # should not raise

    def test_expired_session_removed(self):
        self.bot._update_session("OldUser", {"status": "active"})
        self.bot._sessions["OldUser"]["last_active"] = time.time() - SESSION_EXPIRY_SECONDS - 1
        self.bot._expire_sessions()
        self.assertEqual(self.bot._get_session("OldUser"), {})

    def test_recent_session_not_expired(self):
        self.bot._update_session("NewUser", {"status": "active"})
        self.bot._expire_sessions()
        self.assertNotEqual(self.bot._get_session("NewUser"), {})


# ---------------------------------------------------------------------------
# Session key
# ---------------------------------------------------------------------------


class TestSessionKey(unittest.TestCase):
    def test_key_is_channel(self):
        """Test that session key is based on channel, not sender (collaborative mode)."""
        bot = make_bot()
        msg = make_msg(sender="Alice", channel_idx=1)
        self.assertEqual(bot._session_key(msg), "channel_1")

    def test_different_users_same_channel_same_key(self):
        """Test that different users on same channel share the same session key."""
        bot = make_bot()
        msg1 = make_msg(sender="Alice", channel_idx=1)
        msg2 = make_msg(sender="Bob", channel_idx=1)
        self.assertEqual(bot._session_key(msg1), bot._session_key(msg2))

    def test_different_channels_different_keys(self):
        """Test that different channels have different session keys."""
        bot = make_bot()
        msg1 = make_msg(sender="Alice", channel_idx=1)
        msg2 = make_msg(sender="Alice", channel_idx=2)
        self.assertNotEqual(bot._session_key(msg1), bot._session_key(msg2))


# ---------------------------------------------------------------------------
# Fallback story tree
# ---------------------------------------------------------------------------


class TestFallbackStory(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_start_returns_opening_scene(self):
        result = self.bot._get_fallback_story("Alice", choice=None, theme="fantasy")
        self.assertIn("crossroads", result)
        self.assertIn("1:", result)

    def test_choice_1_advances_to_road(self):
        self.bot._get_fallback_story("Alice", choice=None, theme="fantasy")  # sets node="start"
        result = self.bot._get_fallback_story("Alice", choice="1", theme="fantasy")
        self.assertIn("troll", result.lower())

    def test_terminal_node_has_no_choices(self):
        self.bot._update_session("Alice", {"status": "active", "node": "road", "theme": "fantasy"})
        result = self.bot._get_fallback_story("Alice", choice="1", theme="fantasy")
        self.assertNotIn("1:", result)  # road_pay is terminal
        self.assertEqual(self.bot._get_session("Alice")["status"], "finished")

    def test_scifi_theme_loads_correctly(self):
        result = self.bot._get_fallback_story("Alice", choice=None, theme="scifi")
        self.assertIn("colony ship", result.lower())

    def test_horror_theme_loads_correctly(self):
        result = self.bot._get_fallback_story("Alice", choice=None, theme="horror")
        self.assertIn("manor", result.lower())

    def test_invalid_choice_resets_to_start(self):
        self.bot._update_session("Alice", {"status": "active", "node": "road", "theme": "fantasy"})
        # "9" is not a valid key in road.next
        result = self.bot._get_fallback_story("Alice", choice="9", theme="fantasy")
        # Should reset to "start" node
        self.assertIn("crossroads", result)

    def test_all_fantasy_nodes_fit_max_msg_len(self):
        for node_id, node in _FANTASY_STORY.items():
            msg = self.bot._format_story_message(node["text"], node["choices"])
            self.assertLessEqual(
                len(msg),
                MAX_MSG_LEN,
                f"Fantasy node '{node_id}' formatted message exceeds {MAX_MSG_LEN} chars ({len(msg)})",
            )

    def test_all_scifi_nodes_fit_max_msg_len(self):
        for node_id, node in _SCIFI_STORY.items():
            msg = self.bot._format_story_message(node["text"], node["choices"])
            self.assertLessEqual(
                len(msg),
                MAX_MSG_LEN,
                f"Scifi node '{node_id}' formatted message exceeds {MAX_MSG_LEN} chars ({len(msg)})",
            )

    def test_all_horror_nodes_fit_max_msg_len(self):
        for node_id, node in _HORROR_STORY.items():
            msg = self.bot._format_story_message(node["text"], node["choices"])
            self.assertLessEqual(
                len(msg),
                MAX_MSG_LEN,
                f"Horror node '{node_id}' formatted message exceeds {MAX_MSG_LEN} chars ({len(msg)})",
            )


# ---------------------------------------------------------------------------
# handle_message command dispatch
# ---------------------------------------------------------------------------


class TestHandleMessage(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        # Always use offline fallback so tests don't need network
        self.bot._call_ollama = MagicMock(return_value=None)

    # -- help --

    def test_help_command(self):
        msg = make_msg(content="!help")
        reply = self.bot.handle_message(msg)
        self.assertIn("!adv", reply)
        self.assertIsNotNone(reply)

    def test_help_alias(self):
        msg = make_msg(content="help")
        reply = self.bot.handle_message(msg)
        self.assertIsNotNone(reply)

    # -- !adv start --

    def test_adv_starts_fantasy_by_default(self):
        reply = self.bot.handle_message(make_msg(content="!adv"))
        s = self.bot._get_session(get_session_key(1))
        self.assertEqual(s["theme"], "fantasy")
        self.assertEqual(s["status"], "active")
        self.assertIsNotNone(reply)

    def test_adv_with_explicit_theme(self):
        reply = self.bot.handle_message(make_msg(content="!adv scifi"))
        self.assertEqual(self.bot._get_session(get_session_key(1))["theme"], "scifi")
        self.assertIsNotNone(reply)

    def test_adv_with_horror_theme(self):
        reply = self.bot.handle_message(make_msg(content="!adv horror"))
        self.assertEqual(self.bot._get_session(get_session_key(1))["theme"], "horror")
        self.assertIsNotNone(reply)

    def test_adv_unknown_theme_defaults_to_fantasy(self):
        reply = self.bot.handle_message(make_msg(content="!adv unicorns"))
        self.assertEqual(self.bot._get_session(get_session_key(1))["theme"], "fantasy")
        self.assertIsNotNone(reply)

    def test_start_alias(self):
        reply = self.bot.handle_message(make_msg(content="!start horror"))
        self.assertEqual(self.bot._get_session(get_session_key(1))["theme"], "horror")
        self.assertIsNotNone(reply)

    # -- choices --

    def test_choice_without_session_prompts_start(self):
        reply = self.bot.handle_message(make_msg(content="1"))
        self.assertIn("!adv", reply)

    def test_choice_with_active_session_advances_story(self):
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active", "node": "start", "theme": "fantasy", "history": []})
        reply = self.bot.handle_message(make_msg(content="1"))
        self.assertIsNotNone(reply)
        # Session should still be tracked
        self.assertIn(key, self.bot._sessions)

    def test_choice_on_terminal_node_clears_session(self):
        # road_pay is terminal; node "road" -> choice "1" -> "road_pay"
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active", "node": "road", "theme": "fantasy", "history": []})
        reply = self.bot.handle_message(make_msg(content="1"))
        self.assertIsNotNone(reply)
        # Session should be gone after reaching THE END
        self.assertEqual(self.bot._get_session(key), {})

    # -- !quit / !reset --

    def test_quit_clears_session(self):
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active", "theme": "fantasy"})
        reply = self.bot.handle_message(make_msg(content="!quit"))
        self.assertEqual(self.bot._get_session(key), {})
        self.assertIsNotNone(reply)

    def test_quit_reply_mentions_adv(self):
        reply = self.bot.handle_message(make_msg(content="!quit"))
        self.assertIn("!adv", reply)

    def test_end_alias(self):
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active"})
        reply = self.bot.handle_message(make_msg(content="!end"))
        self.assertEqual(self.bot._get_session(key), {})
        self.assertIsNotNone(reply)

    # -- !status --

    def test_status_no_session(self):
        reply = self.bot.handle_message(make_msg(content="!status"))
        self.assertIn("!adv", reply)

    def test_status_active_session(self):
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active", "theme": "scifi"})
        reply = self.bot.handle_message(make_msg(content="!status"))
        self.assertIn("scifi", reply)

    # -- unknown messages --

    def test_unknown_message_produces_no_reply(self):
        reply = self.bot.handle_message(make_msg(content="random chatter"))
        self.assertIsNone(reply)


# ---------------------------------------------------------------------------
# Collaborative storytelling
# ---------------------------------------------------------------------------


class TestCollaborativeMode(unittest.TestCase):
    """Test collaborative storytelling where multiple users share the same story."""

    def setUp(self):
        self.bot = make_bot()
        # Always use offline fallback so tests don't need network
        self.bot._call_ollama = MagicMock(return_value=None)

    def test_different_users_same_channel_share_story(self):
        """Test that Alice and Bob on same channel see the same story."""
        # Alice starts the adventure
        reply1 = self.bot.handle_message(make_msg(sender="Alice", content="!adv fantasy", channel_idx=1))
        self.assertIsNotNone(reply1)

        # Bob makes a choice - should affect the shared story
        reply2 = self.bot.handle_message(make_msg(sender="Bob", content="1", channel_idx=1))
        self.assertIsNotNone(reply2)

        # Verify both users share the same session
        key = get_session_key(1)
        session = self.bot._get_session(key)
        self.assertEqual(session["status"], "active")
        # The node should have advanced from "start" after Bob's choice
        self.assertNotEqual(session.get("node"), "start")

    def test_different_channels_different_stories(self):
        """Test that different channels have independent stories."""
        # Alice starts on channel 1
        self.bot.handle_message(make_msg(sender="Alice", content="!adv fantasy", channel_idx=1))

        # Bob starts on channel 2
        self.bot.handle_message(make_msg(sender="Bob", content="!adv scifi", channel_idx=2))

        # Verify they have different sessions
        key1 = get_session_key(1)
        key2 = get_session_key(2)
        session1 = self.bot._get_session(key1)
        session2 = self.bot._get_session(key2)

        self.assertEqual(session1["theme"], "fantasy")
        self.assertEqual(session2["theme"], "scifi")

    def test_reset_is_blocked_for_users(self):
        """Test that user-invoked !reset is silently ignored."""
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active", "theme": "fantasy"})

        reply = self.bot.handle_message(make_msg(sender="Bob", content="!reset", channel_idx=1))
        self.assertIsNone(reply)
        # Session should remain active
        self.assertEqual(self.bot._get_session(key).get("status"), "active")

    def test_bot_reset_clears_session(self):
        """Test that _bot_reset() clears all sessions and returns the announcement."""
        key = get_session_key(1)
        self.bot._update_session(key, {"status": "active", "theme": "fantasy"})

        msg = self.bot._bot_reset()
        self.assertIn("24 hours", msg)
        self.assertIn("runtime", msg)
        self.assertEqual(self.bot._sessions, {})

    def test_story_start_time_set_on_adv(self):
        """Test that _story_start_time is set when !adv starts a story."""
        self.assertIsNone(self.bot._story_start_time)
        self.bot.handle_message(make_msg(sender="Alice", content="!adv fantasy", channel_idx=1))
        self.assertIsNotNone(self.bot._story_start_time)

    def test_choice_advances_story_after_adv(self):
        """Test that a valid story choice advances the story after !adv."""
        self.bot.handle_message(make_msg(sender="Alice", content="!adv", channel_idx=1))
        reply = self.bot.handle_message(make_msg(sender="Bob", content="1", channel_idx=1))
        self.assertIsNotNone(reply)

    def test_multiple_users_can_make_choices(self):
        """Test that multiple users can make choices in sequence."""
        # Alice starts
        self.bot.handle_message(make_msg(sender="Alice", content="!adv", channel_idx=1))

        # Bob makes choice 1
        reply1 = self.bot.handle_message(make_msg(sender="Bob", content="1", channel_idx=1))
        self.assertIsNotNone(reply1)

        # Verify session exists and is active, finished, or cleared (if terminal node reached)
        key = get_session_key(1)
        session = self.bot._get_session(key)
        # Session may be cleared if terminal node was reached, otherwise should have status
        if session:
            self.assertIn(session.get("status"), ["active", "finished"])

    def test_cannot_start_new_story_when_active(self):
        """Test that starting a new story is blocked when one is active."""
        # Start a story
        self.bot.handle_message(make_msg(content="!adv fantasy", channel_idx=1))

        # Try to start another - should be blocked
        reply = self.bot.handle_message(make_msg(content="!adv horror", channel_idx=1))
        self.assertIn("in progress", reply.lower())

        # Theme should still be fantasy
        key = get_session_key(1)
        self.assertEqual(self.bot._get_session(key)["theme"], "fantasy")

    def test_can_start_new_story_after_conclusion(self):
        """Test that a new story can start after reaching THE END."""
        key = get_session_key(1)

        # Start and finish a story
        self.bot.handle_message(make_msg(content="!adv fantasy", channel_idx=1))
        self.bot._update_session(key, {"status": "finished"})

        # Should be able to start new story
        reply = self.bot.handle_message(make_msg(content="!adv horror", channel_idx=1))
        self.assertNotIn("in progress", reply.lower())
        self.assertEqual(self.bot._get_session(key)["theme"], "horror")

    def test_story_start_time_tracked(self):
        """Test that story start time is recorded."""
        self.bot.handle_message(make_msg(content="!adv", channel_idx=1))
        self.assertIsNotNone(self.bot._story_start_time)

    def test_24_hour_reset_message_updated(self):
        """Test that reset message mentions 24 hours of runtime not inactivity."""
        msg = self.bot._bot_reset()
        self.assertIn("24 hours", msg.lower())
        self.assertIn("runtime", msg.lower())


# ---------------------------------------------------------------------------
# LLM integration
# ---------------------------------------------------------------------------


class TestLLMIntegration(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.session_key = get_session_key(1)
        self.bot._update_session(self.session_key, {"status": "active", "node": "start", "theme": "fantasy", "history": []})

    def test_llm_response_used_when_available(self):
        llm_text = "You find a chest.\n1:Open it 2:Leave it 3:Kick it"
        with patch.object(self.bot, "_call_ollama", return_value=llm_text):
            result = self.bot._generate_story(self.session_key, choice=None, theme="fantasy")
        self.assertEqual(result, llm_text)

    def test_fallback_used_when_ollama_fails(self):
        with patch.object(self.bot, "_call_ollama", return_value=None):
            result = self.bot._generate_story(self.session_key, choice=None, theme="fantasy")
        self.assertIn("crossroads", result)

    def test_the_end_marks_session_finished(self):
        with patch.object(self.bot, "_call_ollama", return_value="You won! THE END"):
            self.bot._generate_story(self.session_key, choice=None, theme="fantasy")
        self.assertEqual(self.bot._get_session(self.session_key)["status"], "finished")

    def test_llm_result_returns_full_text(self):
        """_generate_story returns full LLM response text."""
        long_story = "A" * 300
        with patch.object(self.bot, "_call_ollama", return_value=long_story):
            result = self.bot._generate_story(self.session_key, choice=None, theme="fantasy")
        # The result from _generate_story is the full text
        self.assertEqual(len(result), 300)


# ---------------------------------------------------------------------------
# Constants / data integrity
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_all_valid_themes_have_story_trees(self):
        for theme in VALID_THEMES:
            self.assertIn(theme, FALLBACK_STORIES)

    def test_all_story_trees_have_start_node(self):
        for theme, tree in FALLBACK_STORIES.items():
            self.assertIn("start", tree, f"Theme '{theme}' missing 'start' node")

    def test_all_next_nodes_exist(self):
        for theme, tree in FALLBACK_STORIES.items():
            for node_id, node in tree.items():
                for choice, next_id in node.get("next", {}).items():
                    self.assertIn(
                        next_id,
                        tree,
                        f"Theme '{theme}', node '{node_id}', choice '{choice}' "
                        f"references missing node '{next_id}'",
                    )

    def test_terminal_nodes_have_no_choices(self):
        for theme, tree in FALLBACK_STORIES.items():
            for node_id, node in tree.items():
                if not node.get("next"):
                    self.assertEqual(
                        node["choices"],
                        [],
                        f"Theme '{theme}', terminal node '{node_id}' should have empty choices",
                    )


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


class TestSessionPersistence(unittest.TestCase):
    def test_sessions_saved_and_reloaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = os.path.join(tmpdir, "sessions.json")
            import adventure_bot as ab_module

            original_path = ab_module.SESSION_FILE
            ab_module.SESSION_FILE = type(ab_module.SESSION_FILE)(session_path)

            try:
                bot = make_bot()
                # Restore real _save_sessions so data actually hits disk
                bot._save_sessions = AdventureBot._save_sessions.__get__(bot, AdventureBot)
                bot._update_session("Alice", {"status": "active", "theme": "scifi"})
                # Force save to disk (batched saves need explicit flush for testing)
                bot._save_sessions(force=True)

                # A fresh bot should reload Alice's session from disk
                bot2 = make_bot()
                bot2._load_sessions()
                s = bot2._get_session("Alice")
                self.assertEqual(s["theme"], "scifi")
            finally:
                ab_module.SESSION_FILE = original_path


if __name__ == "__main__":
    unittest.main(verbosity=2)
