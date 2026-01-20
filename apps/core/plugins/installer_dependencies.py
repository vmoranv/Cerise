"""
Plugin dependency install helpers.
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DependencyMixin:
    async def _install_dependencies(self, plugin_dir: Path, manifest: dict) -> None:
        """Install plugin dependencies."""
        deps = manifest.get("dependencies", {})
        if not deps:
            return

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
            except Exception as exc:
                logger.warning("Failed to install dependencies: %s", exc)
            return

        pip_deps = [f"{name}{version}" for name, version in deps.items()]
        if pip_deps:
            logger.info("Installing dependencies: %s", pip_deps)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "pip",
                    "install",
                    *pip_deps,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.wait()
            except Exception as exc:
                logger.warning("Failed to install dependencies: %s", exc)
