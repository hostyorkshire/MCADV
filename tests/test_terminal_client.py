#!/usr/bin/env python3
"""
Tests for MCADV Terminal Client.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from terminal_client import (  # noqa: E402
    DEFAULT_CONFIG,
    MCADVTerminalClient,
    detect_terminal,
    load_config,
    load_history,
    save_config,
    save_history,
    supports_color,
)


class TestConfigHelpers(unittest.TestCase):
    """Tests for configuration load/save helpers."""

    def test_load_config_returns_defaults_when_missing(self):
        with patch("terminal_client.CONFIG_PATH", Path("/nonexistent/path/config.json")):
            cfg = load_config()
        self.assertEqual(cfg["server_url"], DEFAULT_CONFIG["server_url"])

    def test_load_config_reads_existing_file(self):
        data = {"server_url": "http://test:9999", "theme_preference": "scifi"}
        m = mock_open(read_data=json.dumps(data))
        fake_path = MagicMock(spec=Path)
        fake_path.exists.return_value = True
        fake_path.__truediv__ = Path.__truediv__
        with patch("terminal_client.CONFIG_PATH", fake_path):
            with patch("builtins.open", m):
                cfg = load_config()
        self.assertEqual(cfg["server_url"], "http://test:9999")

    def test_load_config_fills_missing_keys(self):
        partial = {"server_url": "http://partial:1234"}
        fake_path = MagicMock(spec=Path)
        fake_path.exists.return_value = True
        with patch("terminal_client.CONFIG_PATH", fake_path):
            with patch("builtins.open", mock_open(read_data=json.dumps(partial))):
                cfg = load_config()
        for key in DEFAULT_CONFIG:
            self.assertIn(key, cfg)

    def test_load_config_handles_invalid_json(self):
        fake_path = MagicMock(spec=Path)
        fake_path.exists.return_value = True
        with patch("terminal_client.CONFIG_PATH", fake_path):
            with patch("builtins.open", mock_open(read_data="not-json")):
                cfg = load_config()
        self.assertEqual(cfg, DEFAULT_CONFIG)

    def test_save_config_creates_directory(self):
        cfg = DEFAULT_CONFIG.copy()
        fake_path = MagicMock(spec=Path)
        fake_path.parent = MagicMock()
        with patch("terminal_client.CONFIG_PATH", fake_path):
            with patch("builtins.open", mock_open()):
                save_config(cfg)
        fake_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestHistoryHelpers(unittest.TestCase):
    """Tests for history load/save helpers."""

    def test_load_history_returns_empty_list_when_missing(self):
        with patch("terminal_client.HISTORY_PATH", Path("/nonexistent/history.json")):
            hist = load_history()
        self.assertEqual(hist, [])

    def test_load_history_handles_invalid_json(self):
        fake_path = MagicMock(spec=Path)
        fake_path.exists.return_value = True
        with patch("terminal_client.HISTORY_PATH", fake_path):
            with patch("builtins.open", mock_open(read_data="bad")):
                hist = load_history()
        self.assertEqual(hist, [])

    def test_save_history_creates_directory(self):
        fake_path = MagicMock(spec=Path)
        fake_path.parent = MagicMock()
        with patch("terminal_client.HISTORY_PATH", fake_path):
            with patch("builtins.open", mock_open()):
                save_history([{"step": 1}])
        fake_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestPlatformHelpers(unittest.TestCase):
    """Tests for terminal detection helpers."""

    def test_detect_terminal_windows(self):
        with patch("sys.platform", "win32"):
            result = detect_terminal()
        self.assertEqual(result, "windows")

    def test_detect_terminal_uses_term_env(self):
        with patch("sys.platform", "linux"):
            with patch.dict(os.environ, {"TERM": "xterm-256color"}):
                result = detect_terminal()
        self.assertEqual(result, "xterm-256color")

    def test_detect_terminal_unknown(self):
        with patch("sys.platform", "linux"):
            env = {k: v for k, v in os.environ.items() if k != "TERM"}
            with patch.dict(os.environ, env, clear=True):
                result = detect_terminal()
        self.assertEqual(result, "unknown")

    def test_supports_color_false_when_not_tty(self):
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            result = supports_color()
        self.assertFalse(result)


class TestMCADVTerminalClient(unittest.TestCase):
    """Tests for the MCADVTerminalClient class."""

    def setUp(self):
        self.client = MCADVTerminalClient(server_url="http://test:5000")

    # ------------------------------------------------------------------
    # check_server
    # ------------------------------------------------------------------

    def test_check_server_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.get", return_value=mock_resp):
            self.assertTrue(self.client.check_server())

    def test_check_server_non_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("requests.get", return_value=mock_resp):
            self.assertFalse(self.client.check_server())

    def test_check_server_connection_error(self):
        with patch("requests.get", side_effect=requests.ConnectionError):
            self.assertFalse(self.client.check_server())

    def test_check_server_timeout(self):
        with patch("requests.get", side_effect=requests.Timeout):
            self.assertFalse(self.client.check_server())

    # ------------------------------------------------------------------
    # _send_message
    # ------------------------------------------------------------------

    def test_send_message_returns_response_text(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "You are in a forest."}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp):
            result = self.client._send_message("!start fantasy")
        self.assertEqual(result, "You are in a forest.")

    def test_send_message_uses_correct_endpoint(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "ok"}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp) as mock_post:
            self.client._send_message("hello")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/api/message", args[0])

    # ------------------------------------------------------------------
    # start_adventure / make_choice
    # ------------------------------------------------------------------

    def test_start_adventure_sends_theme(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Story begins..."}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = self.client.start_adventure("fantasy")
        self.assertEqual(result, "Story begins...")
        call_kwargs = mock_post.call_args[1]
        self.assertIn("!start fantasy", call_kwargs["json"]["content"])

    def test_make_choice_sends_number(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "You chose 2."}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = self.client.make_choice(2)
        self.assertEqual(result, "You chose 2.")
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["json"]["content"], "2")

    # ------------------------------------------------------------------
    # _parse_response
    # ------------------------------------------------------------------

    def test_parse_response_extracts_choices(self):
        response = (
            "You stand at a crossroads.\n"
            "1. Go north\n"
            "2. Go east\n"
            "3. Turn back\n"
        )
        story, choices = MCADVTerminalClient._parse_response(response)
        self.assertIn("crossroads", story)
        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0], "Go north")
        self.assertEqual(choices[1], "Go east")
        self.assertEqual(choices[2], "Turn back")

    def test_parse_response_no_choices(self):
        response = "The adventure ends. You have won!"
        story, choices = MCADVTerminalClient._parse_response(response)
        self.assertEqual(story, response)
        self.assertEqual(choices, [])

    def test_parse_response_colon_separator(self):
        response = "A fork in the road.\n1: Head left\n2: Head right"
        story, choices = MCADVTerminalClient._parse_response(response)
        self.assertEqual(len(choices), 2)

    def test_parse_response_paren_separator(self):
        response = "Choose your path:\n1) Duck\n2) Dodge"
        story, choices = MCADVTerminalClient._parse_response(response)
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0], "Duck")

    # ------------------------------------------------------------------
    # list_themes
    # ------------------------------------------------------------------

    def test_list_themes_returns_list(self):
        theme_list = self.client.list_themes()
        self.assertIsInstance(theme_list, list)
        self.assertGreater(len(theme_list), 0)

    def test_list_themes_has_required_keys(self):
        theme_list = self.client.list_themes()
        for t in theme_list:
            self.assertIn("name", t)
            self.assertIn("description", t)
            self.assertIn("color", t)

    # ------------------------------------------------------------------
    # quit_adventure / history saving
    # ------------------------------------------------------------------

    def test_quit_adventure_saves_history(self):
        self.client._current_adventure = [{"story": "test", "choices": ["A", "B"]}]
        with patch("terminal_client.save_history") as mock_save:
            self.client.quit_adventure()
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        self.assertEqual(len(saved), 1)

    def test_quit_adventure_clears_session(self):
        self.client._current_adventure = [{"story": "test"}]
        with patch("terminal_client.save_history"):
            self.client.quit_adventure()
        self.assertEqual(self.client._current_adventure, [])
        self.assertIsNone(self.client.session_id)

    def test_quit_adventure_empty_does_not_save(self):
        self.client._current_adventure = []
        with patch("terminal_client.save_history") as mock_save:
            self.client.quit_adventure()
        mock_save.assert_not_called()


class TestCLICommands(unittest.TestCase):
    """Tests for Click CLI commands."""

    def _make_cli_runner(self):
        from click.testing import CliRunner

        return CliRunner()

    def test_health_success(self):
        from click.testing import CliRunner

        from terminal_client import cli

        runner = CliRunner()
        with patch.object(MCADVTerminalClient, "check_server", return_value=True):
            result = runner.invoke(cli, ["health"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("healthy", result.output.lower())

    def test_health_failure(self):
        from click.testing import CliRunner

        from terminal_client import cli

        runner = CliRunner()
        with patch.object(MCADVTerminalClient, "check_server", return_value=False):
            result = runner.invoke(cli, ["health"])
        self.assertNotEqual(result.exit_code, 0)

    def test_themes_lists_themes(self):
        from click.testing import CliRunner

        from terminal_client import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["themes"])
        self.assertEqual(result.exit_code, 0)
        # At least one known theme should appear
        self.assertIn("fantasy", result.output.lower())

    def test_config_shows_current(self):
        from click.testing import CliRunner

        from terminal_client import cli

        runner = CliRunner()
        with patch("terminal_client.load_config", return_value=DEFAULT_CONFIG.copy()):
            result = runner.invoke(cli, ["config"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("server_url", result.output)

    def test_history_no_history(self):
        from click.testing import CliRunner

        from terminal_client import cli

        runner = CliRunner()
        with patch("terminal_client.load_history", return_value=[]):
            result = runner.invoke(cli, ["history"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No saved", result.output)


if __name__ == "__main__":
    unittest.main()
