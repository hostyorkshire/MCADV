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

    def test_long_message_split_into_multiple_parts(self):
        """Messages longer than MAX_MSG_LEN should be split across multiple transmissions."""
        long_text = "A" * (MAX_MSG_LEN + 50)
        self.bot._send_reply(long_text, 1)
        
        # Should be called multiple times
        self.assertGreater(self.bot.mesh.send_message.call_count, 1)
        
        # Each call should be <= MAX_MSG_LEN
        for call in self.bot.mesh.send_message.call_args_list:
            sent_msg = call[0][0]
            self.assertLessEqual(len(sent_msg), MAX_MSG_LEN)
            # Each part should have a part indicator like " (1/2)"
            if self.bot.mesh.send_message.call_count > 1:
                self.assertRegex(sent_msg, r" \(\d+/\d+\)$")

    def test_exact_effective_max_not_split(self):
        """Messages at the effective max (accounting for node overhead) should not be split."""
        # Calculate effective max accounting for node name overhead
        node_overhead = len(self.bot.mesh.node_id) + 2
        effective_max = MAX_MSG_LEN - node_overhead
        
        text = "B" * effective_max
        self.bot._send_reply(text, 1)
        self.bot.mesh.send_message.assert_called_once()
        self.assertEqual(len(last_reply(self.bot)), effective_max)

    def test_correct_channel_idx_forwarded(self):
        self.bot._send_reply("hi", 3)
        self.bot.mesh.send_message.assert_called_once_with("hi", "text", channel_idx=3)
    
    def test_multi_part_messages_have_sequential_numbers(self):
        """Multi-part messages should have sequential part numbers."""
        long_text = "X" * 500  # Long enough to split into multiple parts
        self.bot._send_reply(long_text, 1)
        
        parts = []
        for call in self.bot.mesh.send_message.call_args_list:
            sent_msg = call[0][0]
            parts.append(sent_msg)
        
        # Verify sequential numbering
        import re
        for i, part in enumerate(parts, 1):
            match = re.search(r"\((\d+)/(\d+)\)$", part)
            self.assertIsNotNone(match, f"Part {i} should have part indicator")
            part_num = int(match.group(1))
            total = int(match.group(2))
            self.assertEqual(part_num, i)
            self.assertEqual(total, len(parts))


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
        # Short messages should be short
        self.assertLessEqual(len(msg), MAX_MSG_LEN)

    def test_terminal_node_returns_text_only(self):
        msg = self.bot._format_story_message("You win. THE END", [])
        self.assertEqual(msg, "You win. THE END")
        self.assertNotIn("1:", msg)

    def test_oversized_message_not_capped(self):
        """_format_story_message no longer caps; splitting is done by _send_reply."""
        text = "X" * 180
        choices = ["Go left", "Go right", "Stay put"]
        msg = self.bot._format_story_message(text, choices)
        # The formatted message can exceed MAX_MSG_LEN; _send_reply will split it
        expected_length = len(text) + 1 + len("1:Go left 2:Go right 3:Stay put")
        self.assertEqual(len(msg), expected_length)

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
    def test_key_is_sender(self):
        bot = make_bot()
        msg = make_msg(sender="Alice", channel_idx=1)
        self.assertEqual(bot._session_key(msg), "Alice")


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
        bot.handle_message(make_msg(content="!help", channel_idx=7))
        bot.mesh.send_message.assert_called_once()

    # -- unknown messages --

    def test_unknown_message_produces_no_reply(self):
        self.bot.handle_message(make_msg(content="random chatter"))
        self.bot.mesh.send_message.assert_not_called()


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

    def test_fallback_used_when_ollama_fails(self):
        with patch.object(self.bot, "_call_ollama", return_value=None):
            result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertIn("crossroads", result)

    def test_the_end_marks_session_finished(self):
        with patch.object(self.bot, "_call_ollama", return_value="You won! THE END"):
            self.bot._generate_story("Alice", choice=None, theme="fantasy")
        self.assertEqual(self.bot._get_session("Alice")["status"], "finished")

    def test_llm_result_not_capped(self):
        """_generate_story no longer caps; splitting is done by _send_reply."""
        long_story = "A" * 300
        with patch.object(self.bot, "_call_ollama", return_value=long_story):
            result = self.bot._generate_story("Alice", choice=None, theme="fantasy")
        # The result from _generate_story can be long; _send_reply will split it
        self.assertEqual(len(result), 300)


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


# ---------------------------------------------------------------------------
# Multi-message integration tests
# ---------------------------------------------------------------------------


class TestMultiMessageIntegration(unittest.TestCase):
    """
    Integration tests demonstrating complete multi-message flow.
    These tests verify that long messages are properly split and sent
    across multiple LoRa transmissions.
    """
    
    def test_long_story_from_llm_splits_correctly(self):
        """
        Test that a long LLM response is properly split when sent.
        """
        bot = make_bot()
        bot._call_ollama = MagicMock(return_value=None)
        
        # Create a long LLM response that exceeds MAX_MSG_LEN
        long_story = (
            "You find yourself in a vast underground cavern filled with glowing crystals. "
            "The walls shimmer with an otherworldly light that seems to pulse in rhythm with your heartbeat. "
            "Ancient symbols are carved into the rock face, telling stories of civilizations long forgotten. "
            "Three passages lead deeper into the earth, each one beckoning with mysteries of its own.\n"
            "1:Take the left passage 2:Take the center passage 3:Take the right passage"
        )
        
        # Mock the LLM to return this long story
        with patch.object(bot, "_call_ollama", return_value=long_story):
            # Start an adventure which calls _generate_story and _send_reply
            bot.handle_message(make_msg(sender="TestUser", content="!adv fantasy", channel_idx=1))
        
        # Verify multiple messages were sent
        call_count = bot.mesh.send_message.call_count
        if len(long_story) > MAX_MSG_LEN:
            self.assertGreater(call_count, 1, "Long story should be split into multiple messages")
        
        # Verify each message respects MAX_MSG_LEN
        for call in bot.mesh.send_message.call_args_list:
            msg = call[0][0]
            self.assertLessEqual(len(msg), MAX_MSG_LEN, 
                f"Message '{msg[:50]}...' exceeds MAX_MSG_LEN")
        
        # Verify messages have part indicators if split
        if call_count > 1:
            for i, call in enumerate(bot.mesh.send_message.call_args_list, 1):
                msg = call[0][0]
                self.assertRegex(msg, r"\(\d+/\d+\)$", 
                    f"Part {i} should have part indicator like (1/2)")
    
    def test_reconstructed_message_preserves_content(self):
        """
        Test that split messages can be reconstructed to recover original content.
        """
        bot = make_bot()
        
        # Create a specific long message
        original_message = "X" * 150 + "Y" * 150 + "Z" * 150  # 450 chars
        
        bot._send_reply(original_message, channel_idx=1)
        
        # Collect all parts
        parts = []
        for call in bot.mesh.send_message.call_args_list:
            msg = call[0][0]
            # Remove the part indicator suffix " (X/Y)"
            import re
            match = re.search(r"^(.+?) \(\d+/\d+\)$", msg)
            if match:
                parts.append(match.group(1))
            else:
                parts.append(msg)
        
        # Reconstruct the message
        reconstructed = "".join(parts)
        
        # Verify content is preserved
        self.assertEqual(reconstructed, original_message, 
            "Reconstructed message should match original")
    
    def test_message_exactly_at_effective_limit_not_split(self):
        """
        Verify that messages at the effective limit (accounting for node name overhead) are not split.
        """
        bot = make_bot()
        
        # Calculate effective max accounting for node name overhead
        node_overhead = len(bot.mesh.node_id) + 2
        effective_max = MAX_MSG_LEN - node_overhead
        
        message = "A" * effective_max
        bot._send_reply(message, channel_idx=1)
        
        # Should be sent as a single message
        self.assertEqual(bot.mesh.send_message.call_count, 1)
        sent = bot.mesh.send_message.call_args[0][0]
        self.assertEqual(sent, message)
        self.assertNotRegex(sent, r"\(\d+/\d+\)$", 
            "Message at exactly effective_max should not have part indicator")
    
    def test_message_one_char_over_limit_splits(self):
        """
        Verify that messages just over MAX_MSG_LEN are properly split.
        """
        bot = make_bot()
        
        message = "B" * (MAX_MSG_LEN + 1)
        bot._send_reply(message, channel_idx=1)
        
        # Should be split into 2 parts
        self.assertEqual(bot.mesh.send_message.call_count, 2)
        
        # Both parts should have indicators
        for call in bot.mesh.send_message.call_args_list:
            msg = call[0][0]
            self.assertRegex(msg, r"\(\d+/2\)$")
    
    def test_node_name_overhead_accounted_for(self):
        """
        Test that the node name prefix overhead is properly accounted for.
        
        When messages are sent over LoRa, MeshCore firmware prepends the
        node_id in the format "node_id: content". This overhead must be
        subtracted from the available payload space.
        """
        bot = make_bot()
        
        # Node name is "MCADV" (5 chars) + ": " (2 chars) = 7 chars overhead
        node_overhead = len(bot.mesh.node_id) + 2
        effective_max = MAX_MSG_LEN - node_overhead
        
        # Test message that fits within effective max (should not split)
        message_fits = "X" * effective_max
        bot._send_reply(message_fits, channel_idx=1)
        self.assertEqual(bot.mesh.send_message.call_count, 1,
            "Message at effective_max should not be split")
        
        # Reset mock
        bot.mesh.send_message.reset_mock()
        
        # Test message one char over effective max (should split)
        message_over = "Y" * (effective_max + 1)
        bot._send_reply(message_over, channel_idx=1)
        self.assertGreater(bot.mesh.send_message.call_count, 1,
            "Message over effective_max should be split")
        
        # Verify that when transmitted, each part won't exceed LoRa payload
        for call in bot.mesh.send_message.call_args_list:
            content = call[0][0]
            # Total transmission will be "MCADV: <content>"
            total_transmission = f"{bot.mesh.node_id}: {content}"
            self.assertLessEqual(len(total_transmission), MAX_MSG_LEN,
                f"Total transmission '{total_transmission[:50]}...' exceeds LoRa payload limit")
    
    def test_very_long_message_split_correctly_with_overhead(self):
        """
        Test that very long messages are split into the correct number of parts
        accounting for node name overhead.
        """
        bot = make_bot()
        
        # Create a message that should split into exactly 3 parts
        node_overhead = len(bot.mesh.node_id) + 2
        suffix_space = 8  # " (99/99)"
        chunk_size = MAX_MSG_LEN - node_overhead - suffix_space
        
        # 3 full chunks minus a few chars to avoid boundary issues
        message = "Z" * (chunk_size * 3 - 10)
        bot._send_reply(message, channel_idx=1)
        
        # Should be split into 3 parts
        self.assertEqual(bot.mesh.send_message.call_count, 3)
        
        # Verify each part respects the LoRa payload limit
        for call in bot.mesh.send_message.call_args_list:
            content = call[0][0]
            total_transmission = f"{bot.mesh.node_id}: {content}"
            self.assertLessEqual(len(total_transmission), MAX_MSG_LEN,
                "Each part must fit within LoRa payload limit")


# ---------------------------------------------------------------------------
# Terminal mode tests
# ---------------------------------------------------------------------------


class TestTerminalMode(unittest.TestCase):
    """Test terminal mode functionality."""
    
    def test_terminal_mode_processes_messages(self):
        """Test that terminal mode can process messages through handle_message."""
        bot = make_bot()
        captured_replies = []
        
        def capture_send(text: str, msg_type: str = "text", channel_idx: int = 0):
            captured_replies.append(text)
        
        # Replace send_message with our capture function
        bot.mesh.send_message = capture_send
        
        # Simulate !adv command
        msg = MeshCoreMessage(sender="Terminal", content="!adv", channel_idx=0)
        bot.handle_message(msg)
        
        # Should have received a story response
        self.assertEqual(len(captured_replies), 1)
        self.assertIn("1:", captured_replies[0])
        self.assertIn("2:", captured_replies[0])
        self.assertIn("3:", captured_replies[0])
    
    def test_terminal_mode_handles_choices(self):
        """Test that terminal mode can handle player choices."""
        bot = make_bot()
        captured_replies = []
        
        def capture_send(text: str, msg_type: str = "text", channel_idx: int = 0):
            captured_replies.append(text)
        
        bot.mesh.send_message = capture_send
        
        # Start an adventure
        msg1 = MeshCoreMessage(sender="Terminal", content="!adv", channel_idx=0)
        bot.handle_message(msg1)
        
        # Make a choice
        msg2 = MeshCoreMessage(sender="Terminal", content="1", channel_idx=0)
        bot.handle_message(msg2)
        
        # Should have two replies (start + choice)
        self.assertEqual(len(captured_replies), 2)
        # Both should contain choices (unless we hit a terminal node)
        for reply in captured_replies:
            self.assertTrue(len(reply) > 0)
    
    def test_terminal_mode_handles_themes(self):
        """Test that terminal mode handles different themes."""
        bot = make_bot()
        
        for theme in ["fantasy", "scifi", "horror"]:
            captured_replies = []
            
            def capture_send(text: str, msg_type: str = "text", channel_idx: int = 0):
                captured_replies.append(text)
            
            bot.mesh.send_message = capture_send
            bot._sessions = {}  # Reset sessions
            
            # Start adventure with specific theme
            msg = MeshCoreMessage(sender="Terminal", content=f"!adv {theme}", channel_idx=0)
            bot.handle_message(msg)
            
            # Should receive a story
            self.assertEqual(len(captured_replies), 1)
            self.assertTrue(len(captured_replies[0]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
