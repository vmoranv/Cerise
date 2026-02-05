"""
Plugin install helpers.
"""

import io
import json
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

import httpx

from ..config import InstalledPlugin

logger = logging.getLogger(__name__)


class InstallMixin:
    loader: object
    plugins_dir: Path

    async def install_from_github(
        self,
        repo_url: str,
        branch: str = "main",
    ) -> InstalledPlugin | None:
        """Install plugin from public GitHub repository."""
        parts = repo_url.rstrip("/").replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            logger.error("Invalid GitHub URL: %s", repo_url)
            return None

        owner, repo = parts[0], parts[1]
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

        logger.info("Downloading plugin from %s", zip_url)

        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(zip_url)
                response.raise_for_status()

            return await self._install_from_zip_bytes(
                response.content,
                source="github",
                source_url=repo_url,
            )

        except httpx.HTTPError as exc:
            logger.error("Failed to download from GitHub: %s", exc)
            return None

    async def install_from_zip(self, zip_path: Path | str) -> InstalledPlugin | None:
        """Install plugin from local zip file."""
        zip_path = Path(zip_path)
        if not zip_path.exists():
            logger.error("Zip file not found: %s", zip_path)
            return None

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        return await self._install_from_zip_bytes(
            zip_bytes,
            source="zip",
            source_url=str(zip_path),
        )

    async def install_from_zip_bytes(self, zip_bytes: bytes) -> InstalledPlugin | None:
        """Install plugin from zip bytes (for API upload)."""
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
        """Internal: Install from zip bytes."""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                manifest_path = None
                plugin_root = None

                for name in zf.namelist():
                    if name.endswith("manifest.json"):
                        parts = name.split("/")
                        if len(parts) == 2:
                            plugin_root = parts[0]
                            manifest_path = name
                            break
                        if name == "manifest.json":
                            plugin_root = ""
                            manifest_path = name
                            break

                if not manifest_path:
                    logger.error("No manifest.json found in zip")
                    return None

                manifest_data = json.loads(zf.read(manifest_path))
                raw_name = str(manifest_data.get("name", "") or "").strip()
                plugin_name = raw_name.replace("/", "-").replace("\\", "-")
                plugin_version = manifest_data.get("version", "0.0.0")

                if not plugin_name:
                    logger.error("Plugin name not found in manifest")
                    return None
                if plugin_name in {".", ".."} or ":" in plugin_name:
                    logger.error("Unsafe plugin name in manifest: %s", raw_name)
                    return None

                # Preflight ZipSlip checks before touching the filesystem. In sandboxed
                # environments, best-effort cleanup can be unreliable, so we avoid
                # creating the plugin directory when the zip is unsafe.
                for name in zf.namelist():
                    if plugin_root and not name.startswith(plugin_root + "/"):
                        continue
                    if name.endswith("/"):
                        continue

                    if plugin_root:
                        rel_path = name[len(plugin_root) + 1 :]
                    else:
                        rel_path = name

                    if not rel_path:
                        continue

                    rel = PurePosixPath(rel_path)
                    if rel.is_absolute() or ".." in rel.parts:
                        logger.error("Unsafe path in plugin zip: %s", rel_path)
                        return None
                    if rel.parts and ":" in rel.parts[0]:
                        logger.error("Unsafe path in plugin zip: %s", rel_path)
                        return None

                target_dir = self.plugins_dir / plugin_name
                if target_dir.exists():
                    logger.warning("Removing existing plugin: %s", plugin_name)
                    shutil.rmtree(target_dir)

                target_dir.mkdir(parents=True, exist_ok=True)
                target_root = target_dir.resolve()

                try:
                    for name in zf.namelist():
                        if plugin_root and not name.startswith(plugin_root + "/"):
                            continue
                        if name.endswith("/"):
                            continue

                        if plugin_root:
                            rel_path = name[len(plugin_root) + 1 :]
                        else:
                            rel_path = name

                        if not rel_path:
                            continue

                        rel = PurePosixPath(rel_path)
                        if rel.is_absolute() or ".." in rel.parts:
                            raise ValueError(f"Unsafe path in plugin zip: {rel_path}")
                        if rel.parts and ":" in rel.parts[0]:
                            raise ValueError(f"Unsafe path in plugin zip: {rel_path}")

                        dest = (target_dir / Path(*rel.parts)).resolve()
                        if not dest.is_relative_to(target_root):
                            raise ValueError(f"Unsafe path in plugin zip: {rel_path}")

                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                except Exception:
                    shutil.rmtree(target_dir, ignore_errors=True)
                    raise

                logger.info("Installed plugin: %s v%s", plugin_name, plugin_version)

                plugin = InstalledPlugin(
                    name=plugin_name,
                    version=plugin_version,
                    source=source,
                    source_url=source_url,
                    enabled=True,
                    installed_at=datetime.now().isoformat(),
                )

                self.loader.register_plugin(plugin)

                await self._install_dependencies(target_dir, manifest_data)

                return plugin

        except zipfile.BadZipFile:
            logger.error("Invalid zip file")
            return None
        except Exception as exc:
            logger.exception("Failed to install plugin: %s", exc)
            return None
