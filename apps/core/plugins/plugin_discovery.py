"""
Plugin discovery helpers.
"""

import json
import logging
from pathlib import Path

from .plugin_types import PluginManifest

logger = logging.getLogger(__name__)


class DiscoveryMixin:
    plugins_dir: Path

    async def discover(self) -> list[PluginManifest]:
        """Discover available plugins."""
        manifests = []

        if not self.plugins_dir.exists():
            logger.warning("Plugins directory not found: %s", self.plugins_dir)
            return manifests

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue

            manifest_path = plugin_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        data = json.load(f)
                    manifest = PluginManifest.from_dict(data)
                    manifests.append(manifest)
                    logger.debug("Discovered plugin: %s", manifest.name)
                except Exception as exc:
                    logger.warning("Failed to read manifest %s: %s", manifest_path, exc)

        return manifests
