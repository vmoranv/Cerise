"""
Configuration Loader

Loads and manages configuration from ~/.cerise/ directory.
"""

import logging
import os
from pathlib import Path

import yaml

from .schemas import (
    AppConfig,
    CharacterConfig,
    InstalledPlugin,
    PluginsRegistry,
    ProviderConfig,
    ProvidersConfig,
)

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Get the Cerise data directory (~/.cerise/)"""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("USERPROFILE", "~"))
    else:
        base = Path.home()

    data_dir = base / ".cerise"
    return data_dir


def ensure_data_dir() -> Path:
    """Ensure data directory exists with default structure"""
    data_dir = get_data_dir()

    # Create directories
    dirs = [
        data_dir,
        data_dir / "plugins",
        data_dir / "characters",
        data_dir / "logs",
        data_dir / "cache",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    return data_dir


class ConfigLoader:
    """Loads and manages all configuration"""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or get_data_dir()
        ensure_data_dir()

        self._app_config: AppConfig | None = None
        self._providers_config: ProvidersConfig | None = None
        self._character_config: CharacterConfig | None = None
        self._plugins_registry: PluginsRegistry | None = None

    # ----- App Config -----

    def load_app_config(self) -> AppConfig:
        """Load main app configuration"""
        config_path = self.data_dir / "config.yaml"

        if not config_path.exists():
            self._create_default_app_config(config_path)

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._app_config = AppConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            self._app_config = AppConfig()

        return self._app_config

    def save_app_config(self, config: AppConfig) -> None:
        """Save app configuration"""
        config_path = self.data_dir / "config.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._app_config = config

    def get_app_config(self) -> AppConfig:
        """Get cached or load app config"""
        if self._app_config is None:
            self.load_app_config()
        return self._app_config  # type: ignore

    def _create_default_app_config(self, path: Path) -> None:
        """Create default config file"""
        default = AppConfig()
        data = default.model_dump()

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            f.write("\n# Cerise Configuration\n")
            f.write("# Edit this file to customize settings\n")

    # ----- Providers Config -----

    def load_providers_config(self) -> ProvidersConfig:
        """Load providers configuration"""
        config_path = self.data_dir / "providers.yaml"

        if not config_path.exists():
            self._providers_config = ProvidersConfig()
            return self._providers_config

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._providers_config = ProvidersConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load providers: {e}, using defaults")
            self._providers_config = ProvidersConfig()

        # Expand environment variables in config
        for provider in self._providers_config.providers:
            self._expand_env_vars(provider.config)

        return self._providers_config

    def save_providers_config(self, config: ProvidersConfig) -> None:
        """Save providers configuration"""
        config_path = self.data_dir / "providers.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._providers_config = config

    def get_providers_config(self) -> ProvidersConfig:
        """Get cached or load providers config"""
        if self._providers_config is None:
            self.load_providers_config()
        return self._providers_config  # type: ignore

    def add_provider(self, provider: ProviderConfig) -> None:
        """Add a new provider"""
        config = self.get_providers_config()

        # Check if already exists
        for i, p in enumerate(config.providers):
            if p.id == provider.id:
                config.providers[i] = provider
                self.save_providers_config(config)
                return

        config.providers.append(provider)
        self.save_providers_config(config)

    def remove_provider(self, provider_id: str) -> bool:
        """Remove a provider"""
        config = self.get_providers_config()

        for i, p in enumerate(config.providers):
            if p.id == provider_id:
                config.providers.pop(i)
                self.save_providers_config(config)
                return True

        return False

    def _create_default_providers_config(self, path: Path) -> None:
        """Create default providers config"""
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
        """Expand ${VAR} in config values"""
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[key] = os.environ.get(env_var, "")
            elif isinstance(value, dict):
                self._expand_env_vars(value)

    # ----- Character Config -----

    def load_character_config(self, name: str = "default") -> CharacterConfig:
        """Load character configuration"""
        config_path = self.data_dir / "characters" / f"{name}.yaml"

        if not config_path.exists():
            if name == "default":
                self._create_default_character_config(config_path)
            else:
                raise FileNotFoundError(f"Character not found: {name}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return CharacterConfig(**data)

    def save_character_config(self, config: CharacterConfig, name: str = "default") -> None:
        """Save character configuration"""
        config_path = self.data_dir / "characters" / f"{name}.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

    def list_characters(self) -> list[str]:
        """List available characters"""
        chars_dir = self.data_dir / "characters"
        return [p.stem for p in chars_dir.glob("*.yaml")]

    def _create_default_character_config(self, path: Path) -> None:
        """Create default character config"""
        default = CharacterConfig()

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(default.model_dump(), f, allow_unicode=True)

    # ----- Plugins Registry -----

    def load_plugins_registry(self) -> PluginsRegistry:
        """Load plugins registry"""
        registry_path = self.data_dir / "plugins.json"

        if not registry_path.exists():
            self._plugins_registry = PluginsRegistry()
            return self._plugins_registry

        try:
            import json

            with open(registry_path, encoding="utf-8") as f:
                data = json.load(f)
            self._plugins_registry = PluginsRegistry(**data)
        except Exception as e:
            logger.warning(f"Failed to load plugins registry: {e}")
            self._plugins_registry = PluginsRegistry()

        return self._plugins_registry

    def save_plugins_registry(self, registry: PluginsRegistry) -> None:
        """Save plugins registry"""
        import json

        registry_path = self.data_dir / "plugins.json"

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry.model_dump(), f, indent=2)

        self._plugins_registry = registry

    def get_plugins_registry(self) -> PluginsRegistry:
        """Get cached or load plugins registry"""
        if self._plugins_registry is None:
            self.load_plugins_registry()
        return self._plugins_registry  # type: ignore

    def register_plugin(self, plugin: InstalledPlugin) -> None:
        """Register an installed plugin"""
        registry = self.get_plugins_registry()

        # Update if exists
        for i, p in enumerate(registry.plugins):
            if p.name == plugin.name:
                registry.plugins[i] = plugin
                self.save_plugins_registry(registry)
                return

        registry.plugins.append(plugin)
        self.save_plugins_registry(registry)

    def unregister_plugin(self, name: str) -> bool:
        """Unregister a plugin"""
        registry = self.get_plugins_registry()

        for i, p in enumerate(registry.plugins):
            if p.name == name:
                registry.plugins.pop(i)
                self.save_plugins_registry(registry)
                return True

        return False

    # ----- Plugins Directory -----

    def get_plugins_dir(self) -> Path:
        """Get plugins directory"""
        config = self.get_app_config()
        if config.plugins.plugins_dir:
            return Path(config.plugins.plugins_dir)
        return self.data_dir / "plugins"


# Singleton instance
_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    """Get singleton ConfigLoader instance"""
    global _loader
    if _loader is None:
        _loader = ConfigLoader()
    return _loader
