"""Tests for main entrypoint behavior."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import apps.core.main as main_module
import pytest
from apps.core.config.schemas import AppConfig, LoggingConfig, ServerConfig


def test_resolve_run_options_uses_app_config(monkeypatch: pytest.MonkeyPatch) -> None:
    app_config = AppConfig(
        server=ServerConfig(host="127.0.0.1", port=9100, debug=True),
        logging=LoggingConfig(level="WARNING"),
    )
    fake_loader = SimpleNamespace(get_app_config=lambda: app_config)
    monkeypatch.setattr(main_module, "get_config_loader", lambda: fake_loader)

    args = argparse.Namespace(host=None, port=None, reload=None, log_level=None)
    options = main_module.resolve_run_options(args)

    assert options.host == "127.0.0.1"
    assert options.port == 9100
    assert options.reload is True
    assert options.log_level == "warning"


def test_resolve_run_options_prefers_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    app_config = AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8000, debug=False),
        logging=LoggingConfig(level="INFO"),
    )
    fake_loader = SimpleNamespace(get_app_config=lambda: app_config)
    monkeypatch.setattr(main_module, "get_config_loader", lambda: fake_loader)
    monkeypatch.setenv("CERISE_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("CERISE_SERVER_PORT", "9002")
    monkeypatch.setenv("CERISE_RELOAD", "true")
    monkeypatch.setenv("CERISE_LOG_LEVEL", "DEBUG")

    args = argparse.Namespace(host=None, port=None, reload=None, log_level=None)
    options = main_module.resolve_run_options(args)

    assert options.host == "0.0.0.0"
    assert options.port == 9002
    assert options.reload is True
    assert options.log_level == "debug"


def test_main_run_command_passes_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, main_module.ServerRunOptions] = {}

    def _capture(options: main_module.ServerRunOptions) -> None:
        captured["options"] = options

    monkeypatch.setattr(main_module, "run_server", _capture)

    exit_code = main_module.main(
        ["run", "--host", "127.0.0.1", "--port", "9003", "--no-reload", "--log-level", "debug"]
    )

    assert exit_code == 0
    assert captured["options"].host == "127.0.0.1"
    assert captured["options"].port == 9003
    assert captured["options"].reload is False
    assert captured["options"].log_level == "debug"


def test_main_default_command_runs_server(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, main_module.ServerRunOptions] = {}

    def _capture(options: main_module.ServerRunOptions) -> None:
        captured["options"] = options

    monkeypatch.setattr(main_module, "run_server", _capture)

    exit_code = main_module.main([])

    assert exit_code == 0
    assert captured["options"].host
    assert 1 <= captured["options"].port <= 65535


def test_main_init_config_command(tmp_path: Path) -> None:
    exit_code = main_module.main(["init-config", "--data-dir", str(tmp_path)])
    assert exit_code == 0
    assert (tmp_path / "config.yaml").exists()
    assert (tmp_path / "characters" / "default.yaml").exists()
