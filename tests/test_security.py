"""
Security tests – input validation, rate limiting, XSS prevention,
and channel index validation.
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from security.rate_limiter import RateLimiter  # noqa: E402
from security.validator import InputValidator  # noqa: E402

# =============================================================================
# TestInputValidation
# =============================================================================


class TestInputValidation(unittest.TestCase):

    def setUp(self):
        self.validator = InputValidator()

    # -- validate_message_content --

    def test_short_message_unchanged_length(self):
        msg = "Hello"
        result = self.validator.validate_message_content(msg)
        self.assertIn("Hello", result)

    def test_message_truncated_at_max_length(self):
        long = "A" * 600
        result = self.validator.validate_message_content(long)
        # After HTML escaping the length should still be <= MAX_MESSAGE_LENGTH (500)
        self.assertLessEqual(len(result), InputValidator.MAX_MESSAGE_LENGTH)

    def test_null_bytes_stripped(self):
        result = self.validator.validate_message_content("hello\x00world")
        self.assertNotIn("\x00", result)

    def test_html_angle_brackets_escaped(self):
        result = self.validator.validate_message_content("<script>alert('xss')</script>")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;", result)
        self.assertIn("&gt;", result)

    def test_empty_string_returns_empty(self):
        result = self.validator.validate_message_content("")
        self.assertEqual(result, "")

    def test_normal_adventure_command_preserved(self):
        result = self.validator.validate_message_content("!adv fantasy")
        self.assertIn("!adv", result)
        self.assertIn("fantasy", result)

    # -- sanitize_theme_name --

    def test_theme_lowercased(self):
        result = self.validator.sanitize_theme_name("FANTASY")
        self.assertEqual(result, "fantasy")

    def test_theme_numbers_removed(self):
        result = self.validator.sanitize_theme_name("theme123")
        self.assertEqual(result, "theme")

    def test_theme_special_chars_removed(self):
        result = self.validator.sanitize_theme_name("sci-fi!!")
        self.assertNotIn("-", result)
        self.assertNotIn("!", result)

    def test_theme_underscores_kept(self):
        result = self.validator.sanitize_theme_name("dark_fantasy")
        self.assertIn("_", result)

    def test_theme_truncated(self):
        long_theme = "a" * 100
        result = self.validator.sanitize_theme_name(long_theme)
        self.assertLessEqual(len(result), InputValidator.MAX_THEME_LENGTH)

    def test_empty_theme_returns_empty(self):
        result = self.validator.sanitize_theme_name("")
        self.assertEqual(result, "")


# =============================================================================
# TestRateLimiting
# =============================================================================


class TestRateLimiting(unittest.TestCase):

    def setUp(self):
        # Small limits for fast tests
        self.limiter = RateLimiter(max_messages=5, window_seconds=60)

    def test_first_message_allowed(self):
        self.assertTrue(self.limiter.is_allowed("user1"))

    def test_under_limit_allowed(self):
        for _ in range(4):
            self.assertTrue(self.limiter.is_allowed("user2"))

    def test_at_limit_blocked(self):
        for _ in range(5):
            self.limiter.is_allowed("user3")
        # 6th message should be blocked
        self.assertFalse(self.limiter.is_allowed("user3"))

    def test_different_users_independent(self):
        for _ in range(5):
            self.limiter.is_allowed("heavy_user")
        # heavy_user is rate-limited but light_user is not
        self.assertTrue(self.limiter.is_allowed("light_user"))

    def test_reset_allows_messages_again(self):
        for _ in range(5):
            self.limiter.is_allowed("user4")
        self.assertFalse(self.limiter.is_allowed("user4"))
        self.limiter.reset("user4")
        self.assertTrue(self.limiter.is_allowed("user4"))

    def test_get_remaining_full(self):
        remaining = self.limiter.get_remaining("fresh_user")
        self.assertEqual(remaining, 5)

    def test_get_remaining_decrements(self):
        self.limiter.is_allowed("count_user")
        remaining = self.limiter.get_remaining("count_user")
        self.assertEqual(remaining, 4)

    def test_get_remaining_zero_when_exhausted(self):
        for _ in range(5):
            self.limiter.is_allowed("max_user")
        remaining = self.limiter.get_remaining("max_user")
        self.assertEqual(remaining, 0)

    def test_sliding_window_expires(self):
        # Use a very short window
        limiter = RateLimiter(max_messages=2, window_seconds=1)
        self.assertTrue(limiter.is_allowed("exp_user"))
        self.assertTrue(limiter.is_allowed("exp_user"))
        self.assertFalse(limiter.is_allowed("exp_user"))
        time.sleep(1.1)
        self.assertTrue(limiter.is_allowed("exp_user"))


# =============================================================================
# TestXSSPrevention
# =============================================================================


class TestXSSPrevention(unittest.TestCase):

    def setUp(self):
        self.validator = InputValidator()

    def test_script_tag_escaped(self):
        result = self.validator.validate_message_content("<script>evil()</script>")
        self.assertNotIn("<script>", result)

    def test_img_onerror_escaped(self):
        result = self.validator.validate_message_content('<img src=x onerror="alert(1)">')
        self.assertNotIn("<img", result)

    def test_ampersand_escaped(self):
        result = self.validator.validate_message_content("a & b")
        self.assertIn("&amp;", result)

    def test_quotes_escaped(self):
        result = self.validator.validate_message_content('"quoted"')
        self.assertNotIn('"', result)

    def test_javascript_url_in_content(self):
        result = self.validator.validate_message_content("javascript:alert(1)")
        # Should survive but the angle brackets are gone (there were none here)
        self.assertIsNotNone(result)


# =============================================================================
# TestChannelValidation
# =============================================================================


class TestChannelValidation(unittest.TestCase):

    def setUp(self):
        self.validator = InputValidator()

    def test_zero_is_valid(self):
        self.assertTrue(self.validator.validate_channel_idx(0))

    def test_seven_is_valid(self):
        self.assertTrue(self.validator.validate_channel_idx(7))

    def test_mid_range_valid(self):
        for idx in range(0, 8):
            self.assertTrue(self.validator.validate_channel_idx(idx), f"idx={idx} should be valid")

    def test_negative_invalid(self):
        self.assertFalse(self.validator.validate_channel_idx(-1))

    def test_eight_invalid(self):
        self.assertFalse(self.validator.validate_channel_idx(8))

    def test_large_number_invalid(self):
        self.assertFalse(self.validator.validate_channel_idx(100))

    def test_float_invalid(self):
        self.assertFalse(self.validator.validate_channel_idx(1.5))  # type: ignore[arg-type]

    def test_string_invalid(self):
        self.assertFalse(self.validator.validate_channel_idx("1"))  # type: ignore[arg-type]

    def test_none_invalid(self):
        self.assertFalse(self.validator.validate_channel_idx(None))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
