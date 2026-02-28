import time
from collections import deque
from threading import Lock


class RateLimiter:
    """Sliding-window rate limiter keyed by user ID."""

    def __init__(self, max_messages: int = 10, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._windows: dict = {}
        self._lock = Lock()

    def is_allowed(self, user_id: str) -> bool:
        """Return True if the user has not exceeded their rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            if user_id not in self._windows:
                self._windows[user_id] = deque()
            window = self._windows[user_id]
            # Remove expired timestamps
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) < self.max_messages:
                window.append(now)
                return True
            return False

    def reset(self, user_id: str) -> None:
        """Reset the rate-limit window for a specific user."""
        with self._lock:
            self._windows.pop(user_id, None)

    def get_remaining(self, user_id: str) -> int:
        """Return the number of messages the user may still send in the window."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            if user_id not in self._windows:
                return self.max_messages
            window = self._windows[user_id]
            recent = sum(1 for ts in window if ts >= cutoff)
            return max(0, self.max_messages - recent)
