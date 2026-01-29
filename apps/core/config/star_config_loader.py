"""Star configuration loader."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .schemas import StarEntry, StarRegistry
from .star_schema import apply_schema_defaults, load_schema, schema_to_defaults, validate_schema_config

logger = logging.getLogger(__name__)


class StarConfigLoaderMixin:
    """Star config loading helpers."""

    data_dir: Path
    _star_registry: StarRegistry | None

    def get_star_config_dir(self) -> Path:
        """Return the stars config directory."""
        path = self.data_dir / "stars"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_star_registry_path(self) -> Path:
        """Return the star registry path."""
        return self.get_star_config_dir() / "registry.json"

    def load_star_registry(self) -> StarRegistry:
        """Load star registry from disk."""
        registry_path = self.get_star_registry_path()

        if not registry_path.exists():
            self._star_registry = StarRegistry()
            return self._star_registry

        try:
            with open(registry_path, encoding="utf-8") as f:
                data = json.load(f)
            self._star_registry = StarRegistry(**data)
        except Exception as exc:
            logger.warning("Failed to load star registry: %s", exc)
            self._star_registry = StarRegistry()

        return self._star_registry

    def save_star_registry(self, registry: StarRegistry) -> None:
        """Persist star registry to disk."""
        registry_path = self.get_star_registry_path()

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry.model_dump(), f, indent=2)

        self._star_registry = registry

    def get_star_registry(self) -> StarRegistry:
        """Get cached or load star registry."""
        if self._star_registry is None:
            self.load_star_registry()
        return self._star_registry  # type: ignore[return-value]

    def get_star_entry(self, name: str) -> StarEntry | None:
        """Get a star entry by name."""
        return self.get_star_registry().get_star(name)

    def upsert_star_entry(self, entry: StarEntry) -> None:
        """Insert or update a star entry."""
        registry = self.get_star_registry()
        existing = registry.get_star(entry.name)
        if existing:
            registry.stars = [entry if star.name == entry.name else star for star in registry.stars]
        else:
            registry.stars.append(entry)
        self.save_star_registry(registry)

    def load_star_schema(self, plugin_dir: Path) -> dict[str, Any] | None:
        """Load schema from a plugin directory if present."""
        schema_path = plugin_dir / "_conf_schema.json"
        return load_schema(schema_path)

    def get_star_config_path(self, name: str) -> Path:
        """Return the config path for a star name."""
        safe_name = name.lower().replace("/", "_").replace(" ", "_")
        return self.get_star_config_dir() / f"{safe_name}_config.json"

    def load_star_config(self, name: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Load star config, applying schema defaults when available."""
        config_path = self.get_star_config_path(name)
        if not config_path.exists():
            defaults = schema_to_defaults(schema or {}) if schema else {}
            self.save_star_config(name, defaults)
            return defaults

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            config = data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("Failed to load star config %s: %s", config_path, exc)
            config = {}

        if schema:
            config, changed = apply_schema_defaults(schema, config)
            if changed:
                self.save_star_config(name, config)

        return config

    def save_star_config(self, name: str, config: dict[str, Any]) -> None:
        """Persist star config to disk."""
        config_path = self.get_star_config_path(name)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def validate_star_config(self, config: dict[str, Any], schema: dict[str, Any] | None) -> list[str]:
        """Validate star config against schema."""
        if not schema:
            return []
        return validate_schema_config(schema, config)

    def apply_star_schema(
        self,
        schema: dict[str, Any],
        config: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], bool]:
        """Apply schema defaults to config."""
        return apply_schema_defaults(schema, config)
