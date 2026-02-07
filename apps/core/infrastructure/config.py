"""
Configuration Manager

Unified configuration management with YAML files and environment variable overrides.
"""

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """Centralized configuration management"""

    _instance: "ConfigManager | None" = None
    _config: dict[str, Any] = {}

    def __new__(cls) -> "ConfigManager":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._config = {}
            self._config_paths: list[Path] = []

    def load(self, config_path: str | Path) -> None:
        """Load configuration from YAML file"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        self._config = self._deep_merge(self._config, config)
        self._config_paths.append(path)
        self._apply_env_overrides()

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides

        Format: CERISE_SECTION_KEY=value
        Example: CERISE_AI_DEFAULT_PROVIDER=claude
        """
        prefix = "CERISE_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix) :].lower().split("_")
                self._set_nested(self._config, parts, value)

    def _set_nested(self, config: dict[str, Any], keys: list[str], value: Any) -> None:
        """Set a nested configuration value"""
        for key in keys[:-1]:
            next_value = config.setdefault(key, {})
            if isinstance(next_value, dict):
                config = next_value
            else:
                nested: dict[str, Any] = {}
                config[key] = nested
                config = nested
        # Try to parse as YAML for type conversion
        if isinstance(value, str):
            try:
                config[keys[-1]] = yaml.safe_load(value)
            except yaml.YAMLError:
                config[keys[-1]] = value
            return
        config[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation

        Example: config.get("ai.default_provider")
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split(".")
        self._set_nested(self._config, keys, str(value) if not isinstance(value, (dict, list)) else value)

    def all(self) -> dict[str, Any]:
        """Get all configuration"""
        return self._config.copy()

    def reload(self) -> None:
        """Reload all configuration files"""
        paths = self._config_paths.copy()
        self._config = {}
        self._config_paths = []
        for path in paths:
            self.load(path)

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing)"""
        cls._instance = None
        cls._config = {}


# Global instance
config = ConfigManager()
