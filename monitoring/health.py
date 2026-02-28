import time
from typing import Any, Callable, Dict


class HealthChecker:
    """Reports the health of the bot and its registered sub-components."""

    def __init__(self, version: str = "2.0.0"):
        self._start_time = time.time()
        self.version = version
        self._components: Dict[str, Callable] = {}

    def register_component(self, name: str, checker_fn: Callable) -> None:
        """Register a zero-argument callable that returns True when healthy."""
        self._components[name] = checker_fn

    def check_health(self) -> dict:
        """Return a full health-status dict."""
        component_results: Dict[str, Any] = {}
        overall = True
        for name, fn in self._components.items():
            try:
                ok = bool(fn())
            except Exception as exc:
                ok = False
                component_results[name] = {"healthy": False, "error": str(exc)}
                overall = False
                continue
            component_results[name] = {"healthy": ok}
            if not ok:
                overall = False

        return {
            "healthy": overall,
            "version": self.version,
            "uptime_seconds": self.get_uptime_seconds(),
            "components": component_results,
        }

    def get_uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def is_healthy(self) -> bool:
        return self.check_health()["healthy"]
