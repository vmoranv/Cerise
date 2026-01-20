"""Utility helpers for plugin loader."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def validate_manifest(manifest: dict) -> bool:
    """Validate manifest has required fields."""
    required = ["name", "version", "entry_point", "class_name"]
    for field in required:
        if field not in manifest:
            logger.error("Manifest missing required field: %s", field)
            return False
    return True


def merge_config(schema: dict, user_config: dict | None) -> dict:
    """Merge user config with defaults from schema."""
    config: dict = {}
    properties = schema.get("properties", {})

    for key, prop in properties.items():
        if user_config and key in user_config:
            config[key] = user_config[key]
        elif "default" in prop:
            config[key] = prop["default"]

    if user_config:
        for key, value in user_config.items():
            if key not in config:
                config[key] = value

    return config
