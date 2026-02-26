#!/usr/bin/env python3
"""
Unit tests for MCADV Adventure Bot.

Tests run without any radio hardware by using MeshCore in simulation mode
(serial_port=None) and replacing mesh.send_message with a MagicMock.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import (
    ANNOUNCE_MESSAGE,
    FALLBACK_STORIES,
    MAX_MSG_LEN,
    SESSION_EXPIRY_SECONDS,
    VALID_THEMES,
    AdventureBot,
    _FANTASY_STORY,
    _HORROR_STORY,
    _SCIFI_STORY,
)
from meshcore import MeshCoreMessage


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_bot(**kwargs) -> AdventureBot:
    """
    Create an AdventureBot in simulation mode (no serial port).

    mesh.send_message is replaced with a MagicMock so tests can inspect
    outgoing messages without any radio hardware.  Sessions are reset to
    an empty dict and _save_sessions is mocked so no disk I/O happens,
    preventing state from leaking between tests.
    """
    defaults = dict(
        port=None,
        baud=115200,
        debug=False,
        allowed_channel_idx=None,
        announce=False,
        ollama_url="http://localhost:11434",
        model="test-model",
        openai_key=None,
        groq_key=None,
        shared_mode=False,
    )
    defaults.update(kwargs)
    bot = AdventureBot(**defaults)
    bot.mesh.send_message = MagicMock()
    # Isolate each test: start with clean in-memory sessions, no disk writes
    bot._sessions = {}
    bot._save_sessions = MagicMock()
    return bot


def make_msg(sender: str = "Alice", content: str = "!adv", channel_idx: int = 1) -> MeshCoreMessage:
    """Create a MeshCoreMessage for testing."""
    return MeshCoreMessage(sender=sender, content=content, channel_idx=channel_idx)


def last_reply(bot: AdventureBot) -> str:
    """Return the text argument of the most recent send_message call."""
    return bot.mesh.send_message.call_args[0][0]


# ---------------------------------------------------------------------------
# Message length enforcement
# ---------------------------------------------------------------------------


class TestSendReply(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_short_message_sent_unchanged(self):
        self.bot._send_reply("Hello world", 1)
        self.bot.mesh.send_message.assert_called_once_with("Hello world", "text", channel_idx=1)

    def test_long_message_truncated_to_max_len(self):
        long_text = "A" * (MAX_MSG_LEN + 50)
        self.bot._send_reply(long_text, 1)
        sent = last_reply(self.bot)
        self.assertLessEqual(len(sent), MAX_MSG_LEN)
        self.assertTrue(sent.endswith("…"))

    def test_exact_max_len_not_truncated(self):
        text = "B" * MAX_MSG_LEN
        self.bot._send_reply(text, 1)
        self.assertEqual(len(last_reply(self.bot)), MAX_MSG_LEN)

    def test_correct_channel_idx_forwarded(self):
        self.bot._send_reply("hi", 3)
        self.bot.mesh.send_message.assert_called_once_with("hi", "text", channel_idx=3)


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
        self.assertLessEqual(len(msg), MAX_MSG_LEN)

    def test_terminal_node_returns_text_only(self):
        msg = self.bot._format_story_message("You win. THE END", [])
        self.assertEqual(msg, "You win. THE END")
        self.assertNotIn("1:", msg)

    def test_oversized_message_capped(self):
        text = "X" * 180
        choices = ["Go left", "Go right", "Stay put"]
        msg = self.bot._format_story_message(text, choices)
        self.assertLessEqual(len(msg), MAX_MSG_LEN)

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
# Session key (per-user vs shared mode)
# ---------------------------------------------------------------------------


class TestSessionKey(unittest.TestCase):
    def test_per_user_key_is_sender(self):
        bot = make_bot(shared_mode=False)
        msg = make_msg(sender="Alice", channel_idx=1)
        self.assertEqual(bot._session_key(msg), "Alice")

    def test_shared_key_is_channel(self):
        bot = make_bot(shared_mode=True)
        msg = make_msg(sender="Alice", channel_idx=2)
        self.assertEqual(bot._session_key(msg), "channel_2")

    def test_shared_different_users_same_session(self):
        bot = make_bot(shared_mode=True)
        msg_a = make_msg(sender="Alice", channel_idx=1)
        msg_b = make_msg(sender="Bob", channel_idx=1)
        self.assertEqual(bot._session_key(msg_a), bot._session_key(msg_b))


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
        self.bot._call_openai = MagicMock(return_value=None)
        self.bot._call_groq = MagicMock(return_value=None)

    # -- help --

    def test_help_command(self):
        self.bot.handle_message(make_msg(content="!help"))
        reply = last_reply(self.bot)
        self.assertIn("!adv", reply)
        self.assertLessEqual(len(reply), MAX_MSG_LEN)

    def test_help_alias(self):
        self.bot.handle_message(make_msg(content="help"))
        self.bot.mesh.send_message.assert_called_once()

    # -- !adv start --

    def test_adv_starts_fantasy_by_default(self):
        self.bot.handle_message(make_msg(content="!adv"))
        s = self.bot._get_session("Alice")
        self.assertEqual(s["theme"], "fantasy")
        self.assertEqual(s["status"], "active")

    def test_adv_with_explicit_theme(self):
        self.bot.handle_message(make_msg(content="!adv scifi"))
        self.assertEqual(self.bot._get_session("Alice")["theme"], "scifi")

    def test_adv_with_horror_theme(self):
        self.bot.handle_message(make_msg(content="!adv horror"))
        self.assertEqual(self.bot._get_session("Alice")["theme"], "horror")

    def test_adv_unknown_theme_defaults_to_fantasy(self):
        self.bot.handle_message(make_msg(content="!adv unicorns"))
        self.assertEqual(self.bot._get_session("Alice")["theme"], "fantasy")

    def test_start_alias(self):
        self.bot.handle_message(make_msg(content="!start horror"))
        self.assertEqual(self.bot._get_session("Alice")["theme"], "horror")

    def test_reply_fits_max_msg_len(self):
        self.bot.handle_message(make_msg(content="!adv"))
        self.assertLessEqual(len(last_reply(self.bot)), MAX_MSG_LEN)

    # -- choices --

    def test_choice_without_session_prompts_start(self):
        self.bot.handle_message(make_msg(content="1"))
        self.assertIn("!adv", last_reply(self.bot))

    def test_choice_with_active_session_advances_story(self):
        self.bot._update_session("Alice", {"status": "active", "node": "start", "theme": "fantasy", "history": []})
        self.bot.handle_message(make_msg(content="1"))
        reply = last_reply(self.bot)
        self.assertLessEqual(len(reply), MAX_MSG_LEN)
        # Session should still be tracked
        self.assertIn("Alice", self.bot._sessions)

    def test_choice_on_terminal_node_clears_session(self):
        # road_pay is terminal; node "road" -> choice "1" -> "road_pay"
        self.bot._update_session("Alice", {"status": "active", "node": "road", "theme": "fantasy", "history": []})
        self.bot.handle_message(make_msg(content="1"))
        # Session should be gone after reaching THE END
        self.assertEqual(self.bot._get_session("Alice"), {})

    # -- !quit --

    def test_quit_clears_session(self):
        self.bot._update_session("Alice", {"status": "active", "theme": "fantasy"})
        self.bot.handle_message(make_msg(content="!quit"))
        self.assertEqual(self.bot._get_session("Alice"), {})

    def test_quit_reply_mentions_adv(self):
        self.bot.handle_message(make_msg(content="!quit"))
        self.assertIn("!adv", last_reply(self.bot))

    def test_end_alias(self):
        self.bot._update_session("Alice", {"status": "active"})
        self.bot.handle_message(make_msg(content="!end"))
        self.assertEqual(self.bot._get_session("Alice"), {})

    # -- !status --

    def test_status_no_session(self):
        self.bot.handle_message(make_msg(content="!status"))
        self.assertIn("!adv", last_reply(self.bot))

    def test_status_active_session(self):
        self.bot._update_session("Alice", {"status": "active", "theme": "scifi"})
        self.bot.handle_message(make_msg(content="!status"))
        self.assertIn("scifi", last_reply(self.bot))

    # -- channel filtering --

    def test_wrong_channel_ignored(self):
        bot = make_bot(allowed_channel_idx=2)
        bot.handle_message(make_msg(content="!help", channel_idx=5))
        bot.mesh.send_message.assert_not_called()

    def test_correct_channel_accepted(self):
        bot = make_bot(allowed_channel_idx=1)
        bot.handle_message(make_msg(content="!help", channel_idx=1))
        bot.mesh.send_message.assert_called_once()

    def test_no_filter_accepts_any_channel(self):
        bot = make_bot(allowed_channel_idx=None)
        bot._call_ollama = MagicMock(return_value=None)
        bot._call_openai = MagicMock(return_value=None)
        bot._call_groq = MagicMock(return_value=None)
        bot.handle_message(make_msg(content="!help", channel_idx=7))
        bot.mesh.send_message.assert_called_once()

    # -- unknown messages --

    def test_unknown_message_produces_no_reply(self):
        self.bot.handle_message(make_msg(content="random chatter"))
        self.bot.mesh.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# Shared mode behaviour
# ---------------------------------------------------------------------------


class TestSharedMode(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot(shared_mode=True)
        self.bot._call_ollama = MagicMock(return_value=None)
        self.bot._call_openai = MagicMock(return_value=None)
        self.bot._call_groq = MagicMock(return_value=None)

    def test_two_users_same_channel_share_session(self):
        self.bot.handle_message(make_msg(sender="Alice", content="!adv", channel_idx=1))
        # Bob's session key should be the same channel key
        key_a = self.bot._session_key(make_msg(sender="Alice", channel_idx=1))
        key_b = self.bot._session_key(make_msg(sender="Bob", channel_idx=1))
        self.assertEqual(key_a, key_b)

    def test_shared_start_announces_who_started(self):
        self.bot.handle_message(make_msg(sender="Alice", content="!adv fantasy", channel_idx=1))
        reply = last_reply(self.bot)
        self.assertIn("Alice", reply)

    def test_shared_choice_announces_who_chose(self):
        self.bot._update_session("channel_1", {"status": "active", "node": "start", "theme": "fantasy", "history": []})
        self.bot.handle_message(make_msg(sender="Bob", content="2", channel_idx=1))
        reply = last_reply(self.bot)
        self.assertIn("Bob", reply)


# ---------------------------------------------------------------------------
# LLM integration
# ---------------------------------------------------------------------------


class TestLLMIntegration(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.bot._update_session("Alice", {"status": "active", "node": "start", "theme": "fantasy", "history": []})

    def test_llm_response_used_when_available(self):
        llm_text = "You find a chest.\n1:Open it 2:Leave it 3:Kick it"
        with patch.object(self.bot, "_call_ollama", return_value=llm_text):
            result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertEqual(result, llm_text)

    def test_openai_used_when_ollama_fails(self):
        llm_text = "A dragon appears.\n1:Run 2:Fight 3:Hide"
        with patch.object(self.bot, "_call_ollama", return_value=None):
            with patch.object(self.bot, "_call_openai", return_value=llm_text):
                result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertEqual(result, llm_text)

    def test_groq_used_when_ollama_and_openai_fail(self):
        llm_text = "A wizard blocks the path.\n1:Parley 2:Charge 3:Sneak"
        with patch.object(self.bot, "_call_ollama", return_value=None):
            with patch.object(self.bot, "_call_openai", return_value=None):
                with patch.object(self.bot, "_call_groq", return_value=llm_text):
                    result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertEqual(result, llm_text)

    def test_fallback_used_when_all_llm_fail(self):
        with patch.object(self.bot, "_call_ollama", return_value=None):
            with patch.object(self.bot, "_call_openai", return_value=None):
                with patch.object(self.bot, "_call_groq", return_value=None):
                    result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertIn("crossroads", result)

    def test_the_end_marks_session_finished(self):
        with patch.object(self.bot, "_call_ollama", return_value="You won! THE END"):
            self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertEqual(self.bot._get_session("Alice")["status"], "finished")

    def test_llm_result_capped_at_max_msg_len(self):
        long_story = "A" * 300
        with patch.object(self.bot, "_call_ollama", return_value=long_story):
            result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertLessEqual(len(result), MAX_MSG_LEN)


# ---------------------------------------------------------------------------
# Constants / data integrity
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_announce_message_fits_max_len(self):
        self.assertLessEqual(len(ANNOUNCE_MESSAGE), MAX_MSG_LEN)

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
