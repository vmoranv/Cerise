"""
Plugin Installer

Installs plugins from GitHub or local zip files.
"""

import asyncio
import io
import json
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import httpx

from ..config import InstalledPlugin, get_config_loader

logger = logging.getLogger(__name__)


class PluginInstaller:
    """Handles plugin installation from various sources"""

    def __init__(self, plugins_dir: Path | None = None):
        self.loader = get_config_loader()
        self.plugins_dir = plugins_dir or self.loader.get_plugins_dir()

    async def install_from_github(
        self,
        repo_url: str,
        branch: str = "main",
    ) -> InstalledPlugin | None:
        """
        Install plugin from public GitHub repository.

        Args:
            repo_url: GitHub repo URL (e.g., https://github.com/user/repo)
            branch: Branch to download (default: main)

        Returns:
            InstalledPlugin if successful, None otherwise
        """
        # Parse repo URL
        parts = repo_url.rstrip("/").replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            logger.error(f"Invalid GitHub URL: {repo_url}")
            return None

        owner, repo = parts[0], parts[1]
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

        logger.info(f"Downloading plugin from {zip_url}")

        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(zip_url)
                response.raise_for_status()

            # Extract and install
            return await self._install_from_zip_bytes(
                response.content,
                source="github",
                source_url=repo_url,
            )

        except httpx.HTTPError as e:
            logger.error(f"Failed to download from GitHub: {e}")
            return None

    async def install_from_zip(
        self,
        zip_path: Path | str,
    ) -> InstalledPlugin | None:
        """
        Install plugin from local zip file.

        Args:
            zip_path: Path to zip file

        Returns:
            InstalledPlugin if successful, None otherwise
        """
        zip_path = Path(zip_path)
        if not zip_path.exists():
            logger.error(f"Zip file not found: {zip_path}")
            return None

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        return await self._install_from_zip_bytes(
            zip_bytes,
            source="zip",
            source_url=str(zip_path),
        )

    async def install_from_zip_bytes(
        self,
        zip_bytes: bytes,
    ) -> InstalledPlugin | None:
        """
        Install plugin from zip bytes (for API upload).

        Args:
            zip_bytes: Raw zip file bytes

        Returns:
            InstalledPlugin if successful, None otherwise
        """
        return await self._install_from_zip_bytes(
            zip_bytes,
            source="upload",
            source_url="",
        )

    async def _install_from_zip_bytes(
        self,
        zip_bytes: bytes,
        source: str,
        source_url: str,
    ) -> InstalledPlugin | None:
        """Internal: Install from zip bytes"""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # Find manifest.json
                manifest_path = None
                plugin_root = None

                for name in zf.namelist():
                    if name.endswith("manifest.json"):
                        # Get the directory containing manifest
                        parts = name.split("/")
                        if len(parts) == 2:
                            # e.g., "repo-main/manifest.json"
                            plugin_root = parts[0]
                            manifest_path = name
                            break
                        elif name == "manifest.json":
                            plugin_root = ""
                            manifest_path = name
                            break

                if not manifest_path:
                    logger.error("No manifest.json found in zip")
                    return None

                # Read manifest
                manifest_data = json.loads(zf.read(manifest_path))
                plugin_name = manifest_data.get("name", "").replace("/", "-")
                plugin_version = manifest_data.get("version", "0.0.0")

                if not plugin_name:
                    logger.error("Plugin name not found in manifest")
                    return None

                # Create target directory
                target_dir = self.plugins_dir / plugin_name
                if target_dir.exists():
                    logger.warning(f"Removing existing plugin: {plugin_name}")
                    shutil.rmtree(target_dir)

                target_dir.mkdir(parents=True, exist_ok=True)

                # Extract files
                for name in zf.namelist():
                    if plugin_root and not name.startswith(plugin_root + "/"):
                        continue
                    if name.endswith("/"):
                        continue

                    # Remove root prefix
                    if plugin_root:
                        rel_path = name[len(plugin_root) + 1 :]
                    else:
                        rel_path = name

                    if not rel_path:
                        continue

                    dest = target_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(name) as src, open(dest, "wb") as dst:
                        dst.write(src.read())

                logger.info(f"Installed plugin: {plugin_name} v{plugin_version}")

                # Register plugin
                plugin = InstalledPlugin(
                    name=plugin_name,
                    version=plugin_version,
                    source=source,
                    source_url=source_url,
                    enabled=True,
                    installed_at=datetime.now().isoformat(),
                )

                self.loader.register_plugin(plugin)

                # Install dependencies
                await self._install_dependencies(target_dir, manifest_data)

                return plugin

        except zipfile.BadZipFile:
            logger.error("Invalid zip file")
            return None
        except Exception as e:
            logger.exception(f"Failed to install plugin: {e}")
            return None

    async def uninstall(self, plugin_name: str) -> bool:
        """
        Uninstall a plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            True if successful
        """
        plugin_dir = self.plugins_dir / plugin_name

        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        return self.loader.unregister_plugin(plugin_name)

    async def _install_dependencies(self, plugin_dir: Path, manifest: dict) -> None:
        """Install plugin dependencies"""
        deps = manifest.get("dependencies", {})
        if not deps:
            return

        # Check for requirements.txt
        req_file = plugin_dir / "requirements.txt"
        if req_file.exists():
            logger.info("Installing dependencies from requirements.txt")
            try:
                proc = await asyncio.create_subprocess_exec(
                    "pip",
                    "install",
                    "-r",
                    str(req_file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.wait()
            except Exception as e:
                logger.warning(f"Failed to install dependencies: {e}")
            return

        # Install from manifest dependencies
        pip_deps = [f"{name}{version}" for name, version in deps.items()]
        if pip_deps:
            logger.info(f"Installing dependencies: {pip_deps}")
            try:
                proc = await asyncio.create_subprocess_exec(
                    "pip",
                    "install",
                    *pip_deps,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.wait()
            except Exception as e:
                logger.warning(f"Failed to install dependencies: {e}")

    def list_installed(self) -> list[InstalledPlugin]:
        """List installed plugins"""
        registry = self.loader.get_plugins_registry()
        return registry.plugins

    def get_plugin_info(self, plugin_name: str) -> InstalledPlugin | None:
        """Get plugin info"""
        registry = self.loader.get_plugins_registry()
        for plugin in registry.plugins:
            if plugin.name == plugin_name:
                return plugin
        return None
