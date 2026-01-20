"""
Plugin Installer

Installs plugins from GitHub or local zip files.
"""

from pathlib import Path

from ..config import get_config_loader
from .installer_dependencies import DependencyMixin
from .installer_install import InstallMixin
from .installer_registry import RegistryMixin


class PluginInstaller(InstallMixin, DependencyMixin, RegistryMixin):
    """Handles plugin installation from various sources."""

    def __init__(self, plugins_dir: Path | None = None):
        self.loader = get_config_loader()
        self.plugins_dir = plugins_dir or self.loader.get_plugins_dir()
