"""
Configuration Loader

Loads and manages configuration from ~/.cerise/ directory.
"""

from pathlib import Path

from .app_config_loader import AppConfigLoaderMixin
from .character_config_loader import CharacterConfigLoaderMixin
from .mcp_config_loader import McpConfigLoaderMixin
from .paths import ensure_data_dir, get_data_dir
from .plugins_registry_loader import PluginsRegistryLoaderMixin
from .providers_config_loader import ProvidersConfigLoaderMixin
from .schemas import AppConfig, CharacterConfig, McpConfig, PluginsRegistry, ProvidersConfig, StarRegistry
from .star_config_loader import StarConfigLoaderMixin

__all__ = [
    "ConfigLoader",
    "get_config_loader",
    "get_data_dir",
    "ensure_data_dir",
]


class ConfigLoader(
    AppConfigLoaderMixin,
    ProvidersConfigLoaderMixin,
    McpConfigLoaderMixin,
    CharacterConfigLoaderMixin,
    PluginsRegistryLoaderMixin,
    StarConfigLoaderMixin,
):
    """Loads and manages all configuration."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or get_data_dir()
        ensure_data_dir(self.data_dir)

        self._app_config: AppConfig | None = None
        self._providers_config: ProvidersConfig | None = None
        self._mcp_config: McpConfig | None = None
        self._character_config: CharacterConfig | None = None
        self._plugins_registry: PluginsRegistry | None = None
        self._star_registry: StarRegistry | None = None

    # ----- Plugins Directory -----

    def get_plugins_dir(self) -> Path:
        """Get plugins directory."""
        config = self.get_app_config()
        if config.plugins.plugins_dir:
            return Path(config.plugins.plugins_dir)
        return self.data_dir / "plugins"


# Singleton instance
_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    """Get singleton ConfigLoader instance."""
    global _loader
    if _loader is None:
        _loader = ConfigLoader()
    return _loader
