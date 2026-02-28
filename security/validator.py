import html as html_module

from security.rate_limiter import RateLimiter


class InputValidator:
    """Validates and sanitizes user input."""

    MAX_MESSAGE_LENGTH = 500
    MAX_THEME_LENGTH = 50
    ALLOWED_THEME_CHARS = set("abcdefghijklmnopqrstuvwxyz_")

    def __init__(self):
        self._rate_limiter = RateLimiter()

    def validate_message_content(self, content: str) -> str:
        """Truncate, strip null bytes, and HTML-escape message content."""
        content = content.replace("\x00", "")
        content = content[: self.MAX_MESSAGE_LENGTH]
        content = html_module.escape(content)
        return content

    def sanitize_theme_name(self, theme: str) -> str:
        """Lowercase, filter to allowed characters, and truncate theme name."""
        theme = theme.lower()
        theme = "".join(c for c in theme if c in self.ALLOWED_THEME_CHARS)
        return theme[: self.MAX_THEME_LENGTH]

    def validate_channel_idx(self, idx: int) -> bool:
        """Return True if channel index is in the valid range 0–7."""
        return isinstance(idx, int) and 0 <= idx <= 7

    def check_rate_limit(self, user_id: str) -> bool:
        """Return True if the user is allowed to send a message."""
        return self._rate_limiter.is_allowed(user_id)
