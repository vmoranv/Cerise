# Configuration Module

"""
External configuration management for Cerise.
Data stored in ~/.cerise/
"""

from .loader import ConfigLoader, ensure_data_dir, get_config_loader, get_data_dir
from .schemas import (
    AIConfig,
    AppConfig,
    BusConfig,
    CapabilitiesConfig,
    CapabilityToggle,
    CharacterConfig,
    InstalledPlugin,
    LoggingConfig,
    McpConfig,
    McpServerEntry,
    PersonalityTraits,
    PluginsConfig,
    PluginsRegistry,
    ProviderConfig,
    ProvidersConfig,
    ServerConfig,
    StarAbilityToggle,
    StarEntry,
    StarRegistry,
    ToolCallConfig,
    TTSConfig,
    VoiceConfig,
)

__all__ = [
    # Loader
    "ConfigLoader",
    "get_config_loader",
    "get_data_dir",
    "ensure_data_dir",
    # Schemas
    "AppConfig",
    "ServerConfig",
    "AIConfig",
    "BusConfig",
    "CapabilitiesConfig",
    "CapabilityToggle",
    "StarAbilityToggle",
    "StarEntry",
    "StarRegistry",
    "PluginsConfig",
    "TTSConfig",
    "LoggingConfig",
    "McpConfig",
    "McpServerEntry",
    "ToolCallConfig",
    "ProviderConfig",
    "ProvidersConfig",
    "CharacterConfig",
    "PersonalityTraits",
    "VoiceConfig",
    "InstalledPlugin",
    "PluginsRegistry",
]
