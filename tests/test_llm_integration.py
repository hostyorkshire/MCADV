"""
LLM integration tests – Ollama API calls, timeouts, fallbacks, and response parsing.
All HTTP calls are mocked.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import AdventureBot  # noqa: E402
from meshcore import MeshCoreMessage  # noqa: E402


def _make_bot(**kwargs) -> AdventureBot:
    defaults = dict(
        debug=False,
        ollama_url="http://localhost:11434",
        model="llama3.1:8b",
        http_host="0.0.0.0",
        http_port=5000,
    )
    defaults.update(kwargs)
    bot = AdventureBot(**defaults)
    bot._sessions = {}
    bot._save_sessions = MagicMock()
    return bot


SESSION_KEY = "channel_1"
ACTIVE_SESSION = {"status": "active", "node": "start", "theme": "fantasy", "history": []}


# =============================================================================
# TestOllamaAPI
# =============================================================================


class TestOllamaAPI(unittest.TestCase):
    """Test _call_ollama with mocked HTTP responses."""

    def setUp(self):
        self.bot = _make_bot()
        self.bot._update_session(SESSION_KEY, ACTIVE_SESSION.copy())

    def test_successful_ollama_call_returns_text(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "You find a dragon!"}
        with patch("adventure_bot.requests.post", return_value=mock_response):
            result = self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        self.assertEqual(result, "You find a dragon!")

    def test_http_500_returns_none(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}
        with patch("adventure_bot.requests.post", return_value=mock_response):
            result = self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIsNone(result)

    def test_empty_response_returns_none(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": ""}
        with patch("adventure_bot.requests.post", return_value=mock_response):
            result = self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIsNone(result)

    def test_post_uses_correct_url(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "story"}
        with patch("adventure_bot.requests.post", return_value=mock_response) as mock_post:
            self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        called_url = mock_post.call_args[0][0]
        self.assertIn("/api/generate", called_url)

    def test_post_includes_model(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "story"}
        with patch("adventure_bot.requests.post", return_value=mock_response) as mock_post:
            self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        payload = mock_post.call_args[1]["json"]
        self.assertIn("model", payload)

    def test_post_includes_prompt(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "story"}
        with patch("adventure_bot.requests.post", return_value=mock_response) as mock_post:
            self.bot._call_ollama(SESSION_KEY, choice=None, theme="scifi")
        payload = mock_post.call_args[1]["json"]
        self.assertIn("prompt", payload)
        self.assertIn("scifi", payload["prompt"])

    def test_choice_included_in_prompt(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "story"}
        self.bot._update_session(SESSION_KEY, {"history": ["opening scene"]})
        with patch("adventure_bot.requests.post", return_value=mock_response) as mock_post:
            self.bot._call_ollama(SESSION_KEY, choice="2", theme="fantasy")
        payload = mock_post.call_args[1]["json"]
        self.assertIn("2", payload["prompt"])


# =============================================================================
# TestTimeoutHandling
# =============================================================================


class TestTimeoutHandling(unittest.TestCase):
    """Test that connection/timeout errors are handled gracefully."""

    def setUp(self):
        self.bot = _make_bot()
        self.bot._update_session(SESSION_KEY, ACTIVE_SESSION.copy())

    def test_connection_error_returns_none(self):
        import requests as req
        with patch("adventure_bot.requests.post", side_effect=req.exceptions.ConnectionError("refused")):
            result = self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIsNone(result)

    def test_timeout_error_returns_none(self):
        import requests as req
        with patch("adventure_bot.requests.post", side_effect=req.exceptions.Timeout("timed out")):
            result = self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIsNone(result)

    def test_generic_exception_returns_none(self):
        with patch("adventure_bot.requests.post", side_effect=Exception("unexpected")):
            result = self.bot._call_ollama(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIsNone(result)

    def test_timeout_triggers_fallback(self):
        import requests as req
        with patch("adventure_bot.requests.post", side_effect=req.exceptions.Timeout("timed out")):
            result = self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        # Should fall back to tree story
        self.assertIsNotNone(result)
        self.assertIn("crossroads", result)


# =============================================================================
# TestFallbackBehavior
# =============================================================================


class TestFallbackBehavior(unittest.TestCase):
    """Verify fallback story trees are used when LLM is unavailable."""

    def setUp(self):
        self.bot = _make_bot()
        self.bot._call_ollama = MagicMock(return_value=None)
        self.bot._update_session(SESSION_KEY, ACTIVE_SESSION.copy())

    def test_fallback_for_fantasy(self):
        result = self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIn("crossroads", result)

    def test_fallback_for_scifi(self):
        self.bot._sessions[SESSION_KEY] = {"status": "active", "node": "start", "theme": "scifi", "history": []}
        result = self.bot._generate_story(SESSION_KEY, choice=None, theme="scifi")
        self.assertIn("colony ship", result.lower())

    def test_fallback_for_horror(self):
        self.bot._sessions[SESSION_KEY] = {"status": "active", "node": "start", "theme": "horror", "history": []}
        result = self.bot._generate_story(SESSION_KEY, choice=None, theme="horror")
        self.assertIn("manor", result.lower())

    def test_fallback_for_unknown_theme_uses_fantasy(self):
        self.bot._sessions[SESSION_KEY] = {"status": "active", "node": "start", "theme": "xyz", "history": []}
        result = self.bot._generate_story(SESSION_KEY, choice=None, theme="xyz")
        self.assertIsNotNone(result)

    def test_llm_result_preferred_over_fallback(self):
        self.bot._call_ollama = MagicMock(return_value="LLM generated story")
        result = self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        self.assertEqual(result, "LLM generated story")


# =============================================================================
# TestResponseParsing
# =============================================================================


class TestResponseParsing(unittest.TestCase):
    """Test that LLM responses are parsed and handled correctly."""

    def setUp(self):
        self.bot = _make_bot()
        self.bot._update_session(SESSION_KEY, ACTIVE_SESSION.copy())

    def test_the_end_in_llm_response_marks_finished(self):
        self.bot._call_ollama = MagicMock(return_value="You won! THE END")
        self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        self.assertEqual(self.bot._get_session(SESSION_KEY).get("status"), "finished")

    def test_non_terminal_response_stays_active(self):
        self.bot._call_ollama = MagicMock(return_value="You find a fork.\n1:Left 2:Right 3:Back")
        self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        self.assertEqual(self.bot._get_session(SESSION_KEY).get("status"), "active")

    def test_llm_response_added_to_history(self):
        self.bot._call_ollama = MagicMock(return_value="Scene description")
        self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        history = self.bot._get_session(SESSION_KEY).get("history", [])
        self.assertIn("Scene description", history)

    def test_multiple_llm_calls_build_history(self):
        self.bot._call_ollama = MagicMock(return_value="Scene 1")
        self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        self.bot._call_ollama = MagicMock(return_value="Scene 2")
        self.bot._generate_story(SESSION_KEY, choice="1", theme="fantasy")
        history = self.bot._get_session(SESSION_KEY).get("history", [])
        self.assertGreaterEqual(len(history), 2)

    def test_generate_story_returns_string(self):
        self.bot._call_ollama = MagicMock(return_value=None)
        result = self.bot._generate_story(SESSION_KEY, choice=None, theme="fantasy")
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
