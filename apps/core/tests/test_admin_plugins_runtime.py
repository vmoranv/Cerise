"""Tests for admin plugin runtime routes and auth.

These are unit-style API tests that avoid starting the full service graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from apps.core.api.admin import router as admin_router
from apps.core.infrastructure import StateStore
from fastapi import FastAPI
from fastapi.testclient import TestClient


@dataclass
class _DummyPlugin:
    name: str
    is_running: bool = True
    abilities: list[dict] | None = None

    @property
    def manifest(self):  # noqa: ANN201
        return type(
            "Manifest",
            (),
            {
                "__dict__": {"name": self.name, "version": "0.0.0", "language": "python"},
            },
        )()


class _DummyPluginManager:
    def __init__(self) -> None:
        self.plugins_dir = Path(".")
        self._plugins = {
            "echo-python": _DummyPlugin("echo-python"),
            "echo-node": _DummyPlugin("echo-node"),
        }

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins.keys())

    def get_plugin(self, name: str):  # noqa: ANN201
        return self._plugins.get(name)

    async def health_check(self, name: str) -> bool:
        return bool(self._plugins.get(name))


class _DummyPluginBridge:
    async def register_plugin_abilities(self) -> None:
        return None


class _Services:
    def __init__(self) -> None:
        self.plugin_manager = _DummyPluginManager()
        self.plugin_bridge = _DummyPluginBridge()
        self.state_store = StateStore()


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("CERISE_ADMIN_TOKEN", "test-token")

    app = FastAPI()
    app.include_router(admin_router)
    app.state.services = _Services()
    return TestClient(app)


def test_admin_requires_token(client: TestClient) -> None:
    # No auth -> 401
    resp = client.get("/admin/plugins/runtime")
    assert resp.status_code == 401

    # With auth -> 200
    resp = client.get(
        "/admin/plugins/runtime",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "plugins" in data
    assert {p["name"] for p in data["plugins"]} == {"echo-python", "echo-node"}


def test_admin_plugins_runtime_route_not_shadowed(client: TestClient) -> None:
    # Historically /admin/plugins/runtime could be shadowed by /admin/plugins/{name}.
    resp = client.get(
        "/admin/plugins/runtime",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200
    assert "plugins" in resp.json()


def test_admin_plugin_name_validation(client: TestClient) -> None:
    resp = client.get(
        "/admin/plugins/a:b/runtime/health",
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 400
