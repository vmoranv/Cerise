# Configuration Module

"""
External configuration management for Cerise.
Data stored in ~/.cerise/
"""

from .loader import ConfigLoader, ensure_data_dir, get_config_loader, get_data_dir
from .schemas import (
    AIConfig,
    AppConfig,
    CharacterConfig,
    InstalledPlugin,
    LoggingConfig,
    PersonalityTraits,
    PluginsConfig,
    PluginsRegistry,
    ProviderConfig,
    ProvidersConfig,
    ServerConfig,
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
    "PluginsConfig",
    "TTSConfig",
    "LoggingConfig",
    "ProviderConfig",
    "ProvidersConfig",
    "CharacterConfig",
    "PersonalityTraits",
    "VoiceConfig",
    "InstalledPlugin",
    "PluginsRegistry",
]
