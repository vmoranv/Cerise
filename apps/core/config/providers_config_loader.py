"""
Providers config loading helpers.
"""

import logging
import os
from pathlib import Path

import yaml

from .file_utils import load_config_data, resolve_config_path
from .schemas import ProviderConfig, ProvidersConfig

logger = logging.getLogger(__name__)


class ProvidersConfigLoaderMixin:
    data_dir: Path
    _providers_config: ProvidersConfig | None

    def load_providers_config(self) -> ProvidersConfig:
        """Load providers configuration."""
        config_path = resolve_config_path(self.data_dir / "providers.yaml")

        if not config_path.exists():
            self._providers_config = ProvidersConfig()
            return self._providers_config

        try:
            data = load_config_data(config_path)
            self._providers_config = ProvidersConfig(**data)
        except Exception as exc:
            logger.warning("Failed to load providers: %s, using defaults", exc)
            self._providers_config = ProvidersConfig()

        # Expand environment variables in config
        for provider in self._providers_config.providers:
            self._expand_env_vars(provider.config)

        return self._providers_config

    def save_providers_config(self, config: ProvidersConfig) -> None:
        """Save providers configuration."""
        config_path = self.data_dir / "providers.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._providers_config = config

    def get_providers_config(self) -> ProvidersConfig:
        """Get cached or load providers config."""
        if self._providers_config is None:
            self.load_providers_config()
        return self._providers_config  # type: ignore[return-value]

    def add_provider(self, provider: ProviderConfig) -> None:
        """Add a new provider."""
        config = self.get_providers_config()

        for i, existing in enumerate(config.providers):
            if existing.id == provider.id:
                config.providers[i] = provider
                self.save_providers_config(config)
                return

        config.providers.append(provider)
        self.save_providers_config(config)

    def remove_provider(self, provider_id: str) -> bool:
        """Remove a provider."""
        config = self.get_providers_config()

        for i, provider in enumerate(config.providers):
            if provider.id == provider_id:
                config.providers.pop(i)
                self.save_providers_config(config)
                return True

        return False

    def _create_default_providers_config(self, path: Path) -> None:
        """Create default providers config."""
        default = ProvidersConfig(
            default="openai-default",
            providers=[
                ProviderConfig(
                    id="openai-default",
                    type="openai",
                    name="OpenAI",
                    config={
                        "api_key": "${OPENAI_API_KEY}",
                        "model": "gpt-4o",
                    },
                ),
            ],
        )

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(default.model_dump(), f, allow_unicode=True)

    def _expand_env_vars(self, config: dict) -> None:
        """Expand ${VAR} in config values."""
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[key] = os.environ.get(env_var, "")
            elif isinstance(value, dict):
                self._expand_env_vars(value)
