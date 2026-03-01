#!/usr/bin/env python3
"""
Tests for MCADV Telegram Bot.

These tests use mocks so no real Telegram token or server is required.
"""

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide stub telegram package so tests work without installing python-telegram-bot
try:
    from telegram_bot import (  # noqa: E402
        MCADVTelegramBot,
        _create_choice_keyboard,
        _create_theme_keyboard,
        _escape_md,
        _parse_story_response,
        _session_key_to_channel,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


@unittest.skipUnless(_IMPORT_OK, "python-telegram-bot not installed")
class TestParseStoryResponse(unittest.TestCase):
    """Tests for _parse_story_response()."""

    def test_parses_story_and_choices(self):
        raw = "You stand at a crossroads.\n1:North 2:East 3:South"
        story, choices = _parse_story_response(raw)
        self.assertIn("crossroads", story)
        self.assertEqual(choices, ["North", "East", "South"])

    def test_no_choices_returns_empty_list(self):
        raw = "You have reached THE END."
        story, choices = _parse_story_response(raw)
        self.assertIn("THE END", story)
        self.assertEqual(choices, [])

    def test_empty_input(self):
        story, choices = _parse_story_response("")
        self.assertEqual(story, "")
        self.assertEqual(choices, [])

    def test_multiline_story(self):
        raw = "Line one.\nLine two.\n1:Go left 2:Go right 3:Stay"
        story, choices = _parse_story_response(raw)
        self.assertIn("Line one", story)
        self.assertEqual(len(choices), 3)


@unittest.skipUnless(_IMPORT_OK, "python-telegram-bot not installed")
class TestSessionKeyToChannel(unittest.TestCase):
    """Tests for _session_key_to_channel()."""

    def test_returns_non_negative_int(self):
        result = _session_key_to_channel("user_12345")
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)

    def test_same_key_same_channel(self):
        self.assertEqual(
            _session_key_to_channel("user_99"),
            _session_key_to_channel("user_99"),
        )

    def test_different_keys_different_channels(self):
        # Very unlikely to collide
        self.assertNotEqual(
            _session_key_to_channel("user_1"),
            _session_key_to_channel("group_1"),
        )


@unittest.skipUnless(_IMPORT_OK, "python-telegram-bot not installed")
class TestEscapeMd(unittest.TestCase):
    """Tests for _escape_md()."""

    def test_escapes_special_characters(self):
        result = _escape_md("Hello! This is a test.")
        self.assertIn("\\!", result)
        self.assertIn("\\.", result)

    def test_plain_text_unchanged_structure(self):
        result = _escape_md("Hello world")
        self.assertEqual(result, "Hello world")


@unittest.skipUnless(_IMPORT_OK, "python-telegram-bot not installed")
class TestCreateChoiceKeyboard(unittest.TestCase):
    """Tests for _create_choice_keyboard()."""

    def test_creates_buttons_plus_quit(self):
        choices = ["Go north", "Go east", "Go south"]
        keyboard = _create_choice_keyboard(choices)
        # 3 choice rows + 1 quit row
        self.assertEqual(len(keyboard.inline_keyboard), 4)

    def test_callback_data_format(self):
        choices = ["Option A", "Option B"]
        keyboard = _create_choice_keyboard(choices)
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "choice_1")
        self.assertEqual(keyboard.inline_keyboard[1][0].callback_data, "choice_2")
        self.assertEqual(keyboard.inline_keyboard[-1][0].callback_data, "quit")

    def test_emojis_on_first_three_choices(self):
        choices = ["A", "B", "C"]
        keyboard = _create_choice_keyboard(choices)
        button_text = keyboard.inline_keyboard[0][0].text
        self.assertIn("1️⃣", button_text)


@unittest.skipUnless(_IMPORT_OK, "python-telegram-bot not installed")
class TestCreateThemeKeyboard(unittest.TestCase):
    """Tests for _create_theme_keyboard()."""

    def test_one_button_per_theme(self):
        themes = ["fantasy", "scifi", "horror"]
        keyboard = _create_theme_keyboard(themes)
        self.assertEqual(len(keyboard.inline_keyboard), 3)

    def test_callback_data_format(self):
        themes = ["fantasy"]
        keyboard = _create_theme_keyboard(themes)
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "theme_fantasy")


@unittest.skipUnless(_IMPORT_OK, "python-telegram-bot not installed")
class TestMCADVTelegramBot(unittest.TestCase):
    """Tests for MCADVTelegramBot class."""

    def _make_bot(self, tmp_dir):
        """Create a bot with session file in a temp directory."""
        with patch("telegram_bot.SESSION_FILE", new=pathlib.Path(tmp_dir) / "sessions.json"):
            with patch("telegram.ext.Updater.__init__", return_value=None):
                bot = MCADVTelegramBot.__new__(MCADVTelegramBot)
                bot.token = "test_token"
                bot.server_url = "http://test:5000"
                bot.sessions = {}
                bot._register_handlers = MagicMock()
                bot._load_sessions = MagicMock()
                bot._save_sessions = MagicMock()
                return bot

    def test_session_key_private_chat(self):
        update = MagicMock()
        update.effective_chat.type = "private"
        update.effective_user.id = 12345
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            key = bot._session_key(update)
        self.assertEqual(key, "user_12345")

    def test_session_key_group_chat(self):
        update = MagicMock()
        update.effective_chat.type = "group"
        update.effective_chat.id = 67890
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            key = bot._session_key(update)
        self.assertEqual(key, "group_67890")

    def test_is_group_chat_private(self):
        update = MagicMock()
        update.effective_chat.type = "private"
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            self.assertFalse(bot._is_group_chat(update))

    def test_is_group_chat_group(self):
        update = MagicMock()
        update.effective_chat.type = "group"
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            self.assertTrue(bot._is_group_chat(update))

    @patch("requests.post")
    def test_start_adventure_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"response": "You stand at a crossroads.\n1:North 2:East 3:South"}
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            result = bot.start_adventure("user_1", "fantasy")
        self.assertNotIn("error", result)
        self.assertIn("crossroads", result["story"])
        self.assertEqual(result["choices"], ["North", "East", "South"])

    @patch("requests.post")
    def test_start_adventure_connection_error(self, mock_post):
        mock_post.side_effect = __import__("requests").ConnectionError("refused")
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            result = bot.start_adventure("user_1", "fantasy")
        self.assertTrue(result.get("error"))

    @patch("requests.post")
    def test_make_choice_no_session(self, mock_post):
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            result = bot.make_choice("user_99", 1)
        self.assertTrue(result.get("error"))

    @patch("requests.post")
    def test_make_choice_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"response": "You enter the forest.\n1:Fight 2:Flee 3:Hide"}
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            bot.sessions["user_1"] = {"status": "active", "theme": "fantasy", "channel_idx": 1}
            result = bot.make_choice("user_1", 1)
        self.assertNotIn("error", result)
        self.assertEqual(result["choices"], ["Fight", "Flee", "Hide"])

    def test_format_story_message_with_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            text, keyboard = bot.format_story_message("You enter a cave.", ["Go deeper", "Turn back", "Light a torch"])
        self.assertIn("cave", text)
        # 3 choices + quit button
        self.assertEqual(len(keyboard.inline_keyboard), 4)

    def test_format_story_message_no_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            text, keyboard = bot.format_story_message("THE END. You won!", [])
        self.assertIn("THE END", text)

    def test_session_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_path = pathlib.Path(tmp) / "sessions.json"

            # Create bot and write sessions
            bot = MCADVTelegramBot.__new__(MCADVTelegramBot)
            bot.token = "test"
            bot.server_url = "http://test:5000"
            bot.sessions = {"user_1": {"status": "active", "theme": "fantasy"}}
            bot._register_handlers = MagicMock()

            # Patch SESSION_FILE for save/load
            import telegram_bot as tb

            orig = tb.SESSION_FILE
            tb.SESSION_FILE = session_path
            try:
                bot._save_sessions()
                self.assertTrue(session_path.exists())

                # Load into a new bot
                bot2 = MCADVTelegramBot.__new__(MCADVTelegramBot)
                bot2.sessions = {}
                bot2._load_sessions()
                self.assertIn("user_1", bot2.sessions)
            finally:
                tb.SESSION_FILE = orig

    def test_fetch_themes_returns_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = self._make_bot(tmp)
            themes = bot._fetch_themes()
        self.assertIsInstance(themes, list)
        self.assertIn("fantasy", themes)


if __name__ == "__main__":
    unittest.main()
