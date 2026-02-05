"""Unit tests for plugin dependency install jobs.

We only test the "no deps" fast-path to avoid invoking external toolchains.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from apps.core.infrastructure import StateStore
from apps.core.plugins.deps_jobs import PluginDepsJobs


@pytest.mark.asyncio
async def test_deps_job_skips_when_no_deps(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "p1"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "p1",
                "version": "0.0.1",
                "runtime": {"language": "python", "entry": "main.py", "transport": "stdio"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = StateStore()
    jobs = PluginDepsJobs(store=store, plugins_dir=plugins_dir)

    await jobs.start("p1", force=True)

    # Wait for background task to finish.
    final = None
    for _ in range(100):
        job = await jobs.get("p1")
        if job and job.get("status") in {"success", "error"}:
            final = job
            break
        await asyncio.sleep(0.01)

    assert final is not None
    assert final["status"] == "success"
    assert "skipping" in (final.get("log") or "").lower()


@pytest.mark.asyncio
async def test_deps_job_rejects_invalid_name(tmp_path: Path) -> None:
    store = StateStore()
    jobs = PluginDepsJobs(store=store, plugins_dir=tmp_path)

    with pytest.raises(ValueError):
        await jobs.start("a:b")
