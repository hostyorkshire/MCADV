import threading
import time
from typing import List, Optional

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]


class GatewayPool:
    """Thread-safe pool of bot-server gateway URLs with health tracking."""

    def __init__(self):
        self._gateways: List[dict] = []
        self._lock = threading.Lock()

    def add_gateway(self, url: str) -> None:
        """Register a gateway URL (idempotent)."""
        with self._lock:
            urls = [g["url"] for g in self._gateways]
            if url not in urls:
                self._gateways.append({"url": url, "healthy": True, "last_check": 0.0})

    def get_healthy_gateway(self) -> Optional[str]:
        """Return the URL of the first healthy gateway, or None."""
        with self._lock:
            for gw in self._gateways:
                if gw["healthy"]:
                    return gw["url"]
        return None

    def health_check_all(self) -> None:
        """Probe every registered gateway and update its health status."""
        with self._lock:
            gateways = list(self._gateways)
        for gw in gateways:
            healthy = self._probe(gw["url"])
            with self._lock:
                for g in self._gateways:
                    if g["url"] == gw["url"]:
                        g["healthy"] = healthy
                        g["last_check"] = time.time()

    def _probe(self, url: str) -> bool:
        if _requests is None:
            return False
        try:
            resp = _requests.get(f"{url}/api/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def mark_unhealthy(self, url: str) -> None:
        with self._lock:
            for gw in self._gateways:
                if gw["url"] == url:
                    gw["healthy"] = False

    def mark_healthy(self, url: str) -> None:
        with self._lock:
            for gw in self._gateways:
                if gw["url"] == url:
                    gw["healthy"] = True
