import hashlib
import time
from collections import OrderedDict
from typing import Optional


class ResponseCache:
    """LRU + TTL cache for LLM responses and story nodes."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()

    def _key(self, *parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, ts) in self._cache.items() if now - ts > self.ttl_seconds]
        for k in expired:
            del self._cache[k]

    def _set(self, key: str, value) -> None:
        self._evict_expired()
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, time.time())
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def _get(self, key: str) -> Optional[object]:
        if key not in self._cache:
            return None
        value, ts = self._cache[key]
        if time.time() - ts > self.ttl_seconds:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def cache_llm_response(self, prompt: str, response: str) -> None:
        self._set(self._key("llm", prompt), response)

    def get_cached_response(self, prompt: str) -> Optional[str]:
        return self._get(self._key("llm", prompt))  # type: ignore[return-value]

    def cache_story_node(self, theme: str, node_id: str, data: dict) -> None:
        self._set(self._key("node", theme, node_id), data)

    def get_story_node(self, theme: str, node_id: str) -> Optional[dict]:
        return self._get(self._key("node", theme, node_id))  # type: ignore[return-value]

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
