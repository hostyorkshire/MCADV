import uuid
import time
import threading
from typing import Dict


class MessageTracker:
    """Deduplicates messages using a sliding-window of recently seen IDs."""

    def __init__(self, dedup_window_seconds: int = 60):
        self.dedup_window_seconds = dedup_window_seconds
        self._seen: Dict[str, float] = {}  # message_id -> timestamp
        self._lock = threading.Lock()

    def generate_id(self) -> str:
        """Return a new UUID4 string."""
        return str(uuid.uuid4())

    def is_duplicate(self, message_id: str) -> bool:
        """Return True if *message_id* was seen within the dedup window."""
        now = time.time()
        cutoff = now - self.dedup_window_seconds
        with self._lock:
            ts = self._seen.get(message_id)
            return ts is not None and ts >= cutoff

    def track(self, message_id: str) -> None:
        """Record *message_id* as seen."""
        with self._lock:
            self._seen[message_id] = time.time()

    def cleanup_expired(self) -> int:
        """Remove entries outside the dedup window; return count removed."""
        cutoff = time.time() - self.dedup_window_seconds
        with self._lock:
            expired = [mid for mid, ts in self._seen.items() if ts < cutoff]
            for mid in expired:
                del self._seen[mid]
        return len(expired)
