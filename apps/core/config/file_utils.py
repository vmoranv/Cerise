"""Helpers for config file formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


def resolve_config_path(path: Path) -> Path:
    """Prefer TOML config if present for the same base name."""
    if path.suffix != ".toml":
        toml_path = path.with_suffix(".toml")
        if toml_path.exists():
            return toml_path
    return path


def load_config_data(path: Path) -> dict[str, Any]:
    """Load config data from YAML or TOML."""
    if not path.exists():
        return {}
    if path.suffix == ".toml":
        if not tomllib:
            raise RuntimeError("tomllib is not available")
        with open(path, "rb") as f:
            return tomllib.load(f) or {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
