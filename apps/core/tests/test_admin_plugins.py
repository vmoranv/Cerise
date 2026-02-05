"""Tests for admin plugin install/list/get routes.

Focus:
- list endpoint merges plugins registered in plugins.json with plugins discovered in runtime plugins_dir.
- get endpoint returns manifest details even for unregistered (local) plugins.

These are unit-style API tests that avoid starting the full service graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import apps.core.config.loader as loader_module
import pytest
from apps.core.api.admin import router as admin_router
from apps.core.config.loader import get_config_loader
from apps.core.config.schemas import InstalledPlugin
from apps.core.plugins.plugin_types import PluginManifest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@dataclass
class _LoadedPlugin:
    name: str
    is_running: bool = True


class _DummyPluginManager:
    def __init__(self, plugins_dir: Path) -> None:
        self.plugins_dir = plugins_dir
        self._loaded: dict[str, _LoadedPlugin] = {"disc-only": _LoadedPlugin("disc-only")}

    def list_plugins(self) -> list[str]:
        return list(self._loaded.keys())

    def get_plugin(self, name: str):  # noqa: ANN201
        return self._loaded.get(name)

    async def discover(self) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue
            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifests.append(PluginManifest.from_dict(data))
        return manifests


class _DummyPluginBridge:
    async def register_plugin_abilities(self) -> None:
        return None


class _Services:
    def __init__(self, plugins_dir: Path) -> None:
        self.plugin_manager = _DummyPluginManager(plugins_dir)
        self.plugin_bridge = _DummyPluginBridge()


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    data_dir = tmp_path / "cerise_data"
    monkeypatch.setenv("CERISE_DATA_DIR", str(data_dir))
    monkeypatch.setattr(loader_module, "_loader", None)

    monkeypatch.setenv("CERISE_ADMIN_TOKEN", "test-token")

    # Registered plugin (exists only in plugins.json)
    loader = get_config_loader()
    loader.register_plugin(
        InstalledPlugin(
            name="reg-only",
            version="1.2.3",
            source="zip",
            enabled=True,
        )
    )

    # Discovered plugin (exists only on disk in runtime plugins_dir)
    plugins_dir = tmp_path / "runtime_plugins"
    (plugins_dir / "disc-only").mkdir(parents=True, exist_ok=True)
    (plugins_dir / "disc-only" / "manifest.json").write_text(
        json.dumps(
            {
                "name": "disc-only",
                "version": "0.1.0",
                "runtime": {"language": "python", "entry": "main.py"},
            }
        ),
        encoding="utf-8",
    )

    app = FastAPI()
    app.include_router(admin_router)
    app.state.services = _Services(plugins_dir)
    return TestClient(app)


def test_admin_plugins_list_merges_registered_and_discovered(client: TestClient) -> None:
    resp = client.get(
        "/admin/plugins",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()

    names = {p["name"] for p in data["plugins"]}
    assert names == {"reg-only", "disc-only"}

    disc = next(p for p in data["plugins"] if p["name"] == "disc-only")
    assert disc["registered"] is False
    assert disc["discovered"] is True
    assert disc["loaded"] is True
    assert disc["running"] is True
    assert disc["display_name"] == "disc-only"
    assert disc["star_enabled"] is True
    assert disc["star_allow_tools"] is True

    reg = next(p for p in data["plugins"] if p["name"] == "reg-only")
    assert reg["registered"] is True
    assert reg["discovered"] is False
    assert reg["loaded"] is False
    assert reg["running"] is False
    assert reg["star_enabled"] is True
    assert reg["star_allow_tools"] is True


def test_admin_plugins_get_returns_manifest_for_unregistered_plugin(client: TestClient) -> None:
    resp = client.get(
        "/admin/plugins/disc-only",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["registered"] is False
    assert data["discovered"] is True
    assert data["loaded"] is True
    assert data["running"] is True

    assert data["manifest"]["name"] == "disc-only"
    assert data["manifest"]["version"] == "0.1.0"
