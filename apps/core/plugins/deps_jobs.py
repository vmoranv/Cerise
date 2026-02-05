"""Plugin dependency installation jobs (best-effort, opt-in).

This is intentionally lightweight: it provides a small amount of durability via StateStore
and avoids introducing a full workflow engine.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import get_config_loader
from ..infrastructure import StateStore
from .name_safety import validate_plugin_name

logger = logging.getLogger(__name__)

_TASKS: dict[str, asyncio.Task[None]] = {}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha1_bytes(*parts: bytes) -> str:
    h = hashlib.sha1()
    for part in parts:
        h.update(part)
    return h.hexdigest()


def _truncate(text: str, *, max_chars: int = 20000) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n...[truncated]"


async def _run_cmd(cmd: list[str], *, cwd: Path) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    stdout = stdout_b.decode(errors="replace")
    stderr = stderr_b.decode(errors="replace")
    return int(proc.returncode or 0), stdout, stderr


class PluginDepsJobs:
    """Run and track plugin dependency installs."""

    def __init__(self, *, store: StateStore, plugins_dir: Path) -> None:
        self._store = store
        self._plugins_dir = plugins_dir

    def _key(self, plugin_name: str) -> str:
        safe = plugin_name.replace("/", "_")
        return f"plugins.deps.{safe}"

    def get_sync(self, plugin_name: str) -> dict[str, Any] | None:
        try:
            plugin_name = validate_plugin_name(plugin_name)
        except ValueError:
            return None
        return self._store.get_sync(self._key(plugin_name))

    async def get(self, plugin_name: str) -> dict[str, Any] | None:
        try:
            plugin_name = validate_plugin_name(plugin_name)
        except ValueError:
            return None
        return await self._store.get(self._key(plugin_name))

    async def start(self, plugin_name: str, *, force: bool = False) -> dict[str, Any]:
        plugin_name = validate_plugin_name(plugin_name)
        plugin_dir = self._plugins_dir / plugin_name
        manifest_path = plugin_dir / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError(f"Plugin manifest not found: {manifest_path}")

        manifest_bytes = manifest_path.read_bytes()
        req_path = plugin_dir / "requirements.txt"
        req_bytes = req_path.read_bytes() if req_path.exists() else b""
        digest = _sha1_bytes(manifest_bytes, req_bytes)

        key = self._key(plugin_name)
        existing = self._store.get_sync(key)

        if existing and not force:
            if existing.get("status") in {"pending", "running"}:
                return existing
            if existing.get("status") == "success" and existing.get("digest") == digest:
                return existing

        job: dict[str, Any] = {
            "plugin": plugin_name,
            "digest": digest,
            "status": "pending",
            "started_at": _utc_now(),
            "finished_at": None,
            "log": "",
            "error": None,
        }
        self._store.set_sync(key, job)

        task = _TASKS.get(plugin_name)
        if task and not task.done():
            return job

        _TASKS[plugin_name] = asyncio.create_task(self._run(plugin_name, key, job))
        return job

    async def _run(self, plugin_name: str, key: str, job: dict[str, Any]) -> None:
        loader = get_config_loader()
        app_config = loader.get_app_config()
        venv_dir_name = app_config.plugins.python_venv_dir or ".venv"

        plugin_dir = self._plugins_dir / plugin_name
        manifest_path = plugin_dir / "manifest.json"

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            job.update(
                {
                    "status": "error",
                    "finished_at": _utc_now(),
                    "error": f"Failed to read manifest.json: {exc}",
                },
            )
            self._store.set_sync(key, job)
            return

        runtime = manifest.get("runtime") if isinstance(manifest, dict) else None
        runtime = runtime if isinstance(runtime, dict) else {}
        language = (runtime.get("language") or manifest.get("language") or "python").lower()

        job["status"] = "running"
        self._store.set_sync(key, job)

        def append(section: str, text: str) -> None:
            payload = f"\n[{section}]\n{text}".strip()
            job["log"] = _truncate((job.get("log") or "") + "\n" + payload)
            self._store.set_sync(key, job)

        try:
            if language == "python":
                req_file = plugin_dir / "requirements.txt"
                deps = manifest.get("dependencies") if isinstance(manifest, dict) else None
                deps = deps if isinstance(deps, dict) else {}

                if not req_file.exists() and not deps:
                    append("python", "No requirements.txt or dependencies found; skipping.")
                    job.update({"status": "success", "finished_at": _utc_now()})
                    self._store.set_sync(key, job)
                    return

                venv_dir = plugin_dir / venv_dir_name
                python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

                if not python_path.exists():
                    code, out, err = await _run_cmd(
                        [sys.executable, "-m", "venv", str(venv_dir)],
                        cwd=plugin_dir,
                    )
                    append("venv", out + ("\n" + err if err else ""))
                    if code != 0:
                        raise RuntimeError(f"venv creation failed (code={code})")

                python_exec = str(python_path) if python_path.exists() else sys.executable

                if req_file.exists():
                    cmd = [python_exec, "-m", "pip", "install", "-r", str(req_file)]
                else:
                    pip_deps = [f"{name}{version}" for name, version in deps.items()]
                    cmd = [python_exec, "-m", "pip", "install", *pip_deps]

                code, out, err = await _run_cmd(cmd, cwd=plugin_dir)
                append("pip", out + ("\n" + err if err else ""))
                if code != 0:
                    raise RuntimeError(f"pip install failed (code={code})")

            elif language in {"node", "nodejs", "javascript"}:
                pkg = plugin_dir / "package.json"
                if not pkg.exists():
                    append("node", "No package.json found; skipping.")
                else:
                    code, out, err = await _run_cmd(["npm", "install", "--omit=dev"], cwd=plugin_dir)
                    append("npm", out + ("\n" + err if err else ""))
                    if code != 0:
                        raise RuntimeError(f"npm install failed (code={code})")

            elif language in {"go", "golang"}:
                gomod = plugin_dir / "go.mod"
                if not gomod.exists():
                    append("go", "No go.mod found; skipping.")
                else:
                    code, out, err = await _run_cmd(["go", "mod", "download"], cwd=plugin_dir)
                    append("go", out + ("\n" + err if err else ""))
                    if code != 0:
                        raise RuntimeError(f"go mod download failed (code={code})")

            else:
                append("skip", f"Dependency install not supported for language '{language}'.")

            job.update({"status": "success", "finished_at": _utc_now(), "error": None})
            self._store.set_sync(key, job)
        except Exception as exc:
            logger.exception("Dependency install job failed for %s", plugin_name)
            append("error", str(exc))
            job.update({"status": "error", "finished_at": _utc_now(), "error": str(exc)})
            self._store.set_sync(key, job)
