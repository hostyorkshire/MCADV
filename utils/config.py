import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Hierarchical configuration with dot-notation access and env-var overrides."""

    DEFAULTS: Dict[str, Any] = {
        "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "llm": {
            "backend": "ollama",
            "url": "http://localhost:11434",
            "model": "llama3.1:8b",
            "timeout": 30,
            "max_retries": 3,
        },
        "radio": {"port": None, "baud": 115200, "auto_detect": True},
        "security": {
            "rate_limit": {"enabled": True, "max_messages_per_minute": 10},
            "input_validation": {"max_message_length": 500},
        },
        "monitoring": {"metrics_enabled": True, "health_check_interval": 60},
        "features": {"story_saves": True, "web_dashboard": True, "llm_generation": True},
    }

    def __init__(self, config_path: Optional[Path] = None):
        import copy

        self._data: Dict[str, Any] = copy.deepcopy(self.DEFAULTS)
        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as fh:
                    loaded = json.load(fh)
                self._merge(self._data, loaded)
            except Exception:
                pass

    def _merge(self, base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value using dot notation, e.g. 'server.port'."""
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def get_all(self) -> Dict:
        import copy

        return copy.deepcopy(self._data)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config whose values can be overridden by environment variables."""
        instance = cls()
        mapping = {
            "BOT_HOST": "server.host",
            "BOT_PORT": "server.port",
            "BOT_DEBUG": "server.debug",
            "OLLAMA_URL": "llm.url",
            "OLLAMA_MODEL": "llm.model",
            "RADIO_PORT": "radio.port",
            "RADIO_BAUD": "radio.baud",
        }
        for env_var, dot_key in mapping.items():
            val = os.environ.get(env_var)
            if val is not None:
                parts = dot_key.split(".")
                node = instance._data
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = val
        return instance
