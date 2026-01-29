"""Tests for config path helpers."""

from pathlib import Path

from apps.core.config.paths import get_data_dir


def test_get_data_dir_respects_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CERISE_DATA_DIR", "custom-data-dir")
    assert get_data_dir() == Path("custom-data-dir")
