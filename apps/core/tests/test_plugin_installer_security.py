"""Security-focused tests for plugin installation."""

from __future__ import annotations

import io
import json
import zipfile

import apps.core.plugins.installer as installer_mod
import pytest
from apps.core.config.loader import ConfigLoader
from apps.core.plugins.installer import PluginInstaller


@pytest.mark.asyncio
async def test_plugin_zip_path_traversal_is_rejected(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "cerise_data"
    loader = ConfigLoader(data_dir)
    monkeypatch.setattr(installer_mod, "get_config_loader", lambda: loader)

    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "name": "bad-plugin",
                    "version": "0.0.1",
                    "runtime": {"language": "python", "entry": "main.py"},
                }
            ),
        )
        zf.writestr("../evil.txt", "owned")

    installer = PluginInstaller(plugins_dir=plugins_dir)
    plugin = await installer.install_from_zip_bytes(buf.getvalue())

    assert plugin is None
    assert not (plugins_dir / "bad-plugin").exists()
    assert not (plugins_dir / "evil.txt").exists()
