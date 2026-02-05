"""
Plugin dependency install helpers.
"""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class DependencyMixin:
    async def _install_dependencies(self, plugin_dir: Path, manifest: dict) -> None:
        """Install plugin dependencies."""
        try:
            config = self.loader.get_app_config()  # type: ignore[attr-defined]
            plugins_config = config.plugins
            auto_install = bool(getattr(plugins_config, "auto_install_dependencies", False))
            venv_dir_name = str(getattr(plugins_config, "python_venv_dir", ".venv") or ".venv")
        except Exception:
            auto_install = False
            venv_dir_name = ".venv"

        if not auto_install:
            return

        runtime = manifest.get("runtime") if isinstance(manifest, dict) else None
        runtime = runtime if isinstance(runtime, dict) else {}
        language = (runtime.get("language") or manifest.get("language") or "python").lower()

        deps = manifest.get("dependencies") if isinstance(manifest, dict) else None
        deps = deps if isinstance(deps, dict) else {}

        req_file = plugin_dir / "requirements.txt"
        if language == "python" and req_file.exists():
            logger.info("Installing python dependencies from requirements.txt")
            try:
                venv_dir = plugin_dir / venv_dir_name
                python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                if not python_path.exists():
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "-m",
                        "venv",
                        str(venv_dir),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.wait()

                python_exec = str(python_path) if python_path.exists() else sys.executable
                proc = await asyncio.create_subprocess_exec(
                    python_exec,
                    "-m",
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

        if language == "python":
            pip_deps = [f"{name}{version}" for name, version in deps.items()]
            if pip_deps:
                logger.info("Installing python dependencies: %s", pip_deps)
                try:
                    venv_dir = plugin_dir / venv_dir_name
                    python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                    if not python_path.exists():
                        proc = await asyncio.create_subprocess_exec(
                            sys.executable,
                            "-m",
                            "venv",
                            str(venv_dir),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await proc.wait()

                    python_exec = str(python_path) if python_path.exists() else sys.executable

                    proc = await asyncio.create_subprocess_exec(
                        python_exec,
                        "-m",
                        "pip",
                        "install",
                        *pip_deps,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.wait()
                except Exception as exc:
                    logger.warning("Failed to install dependencies: %s", exc)
            return

        if language in {"node", "nodejs", "javascript"}:
            pkg = plugin_dir / "package.json"
            if not pkg.exists():
                return
            logger.info("Installing node dependencies in %s", plugin_dir)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "npm",
                    "install",
                    "--omit=dev",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(plugin_dir),
                )
                await proc.wait()
            except Exception as exc:
                logger.warning("Failed to install node dependencies: %s", exc)
            return

        if language in {"go", "golang"}:
            gomod = plugin_dir / "go.mod"
            if not gomod.exists():
                return
            logger.info("Installing go module dependencies in %s", plugin_dir)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "go",
                    "mod",
                    "download",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(plugin_dir),
                )
                await proc.wait()
            except Exception as exc:
                logger.warning("Failed to install go dependencies: %s", exc)
