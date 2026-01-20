"""Types for the plugin loader."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import BaseAbility


@dataclass
class LoadedPlugin:
    """Represents a loaded plugin."""

    name: str
    manifest: dict
    module: Any
    instance: BaseAbility

    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.0.0")

    @property
    def display_name(self) -> str:
        return self.manifest.get("display_name", self.name)
