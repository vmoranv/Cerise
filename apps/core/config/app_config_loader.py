"""
App config loading helpers.
"""

import logging
from pathlib import Path

import yaml

from .schemas import AppConfig

logger = logging.getLogger(__name__)


class AppConfigLoaderMixin:
    data_dir: Path
    _app_config: AppConfig | None

    def load_app_config(self) -> AppConfig:
        """Load main app configuration."""
        config_path = self.data_dir / "config.yaml"

        if not config_path.exists():
            self._create_default_app_config(config_path)

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._app_config = AppConfig(**data)
        except Exception as exc:
            logger.warning("Failed to load config: %s, using defaults", exc)
            self._app_config = AppConfig()

        return self._app_config

    def save_app_config(self, config: AppConfig) -> None:
        """Save app configuration."""
        config_path = self.data_dir / "config.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._app_config = config

    def get_app_config(self) -> AppConfig:
        """Get cached or load app config."""
        if self._app_config is None:
            self.load_app_config()
        return self._app_config  # type: ignore[return-value]

    def _create_default_app_config(self, path: Path) -> None:
        """Create default config file."""
        default = AppConfig()
        data = default.model_dump()

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            f.write("\n# Cerise Configuration\n")
            f.write("# Edit this file to customize settings\n")
