"""Star config schema helpers."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

_DEFAULT_SCHEMA_VALUES: dict[str, Any] = {
    "bool": False,
    "int": 0,
    "float": 0.0,
    "string": "",
    "text": "",
    "list": [],
    "template_list": [],
}


def load_schema(path: Path) -> dict[str, Any] | None:
    """Load a star config schema from JSON."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)
    return schema if isinstance(schema, dict) else None


def schema_to_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    """Build default config data from a schema."""
    defaults: dict[str, Any] = {}
    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        value_type = spec.get("type")
        if value_type == "object":
            defaults[key] = schema_to_defaults(spec.get("items", {}))
            continue
        defaults[key] = _copy_default(_schema_default(spec))
    return defaults


def apply_schema_defaults(schema: dict[str, Any], config: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    """Apply schema defaults and drop unknown keys."""
    source = config if isinstance(config, dict) else {}
    result: dict[str, Any] = {}
    changed = False

    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        value_type = spec.get("type")
        if value_type == "object":
            nested_source = source.get(key)
            if isinstance(nested_source, dict):
                nested, nested_changed = apply_schema_defaults(spec.get("items", {}), nested_source)
                result[key] = nested
                changed |= nested_changed
            else:
                result[key] = schema_to_defaults(spec.get("items", {}))
                changed = True
            continue
        if key not in source:
            result[key] = _copy_default(_schema_default(spec))
            changed = True
            continue
        result[key] = source[key]

    if set(source.keys()) - set(schema.keys()):
        changed = True

    return result, changed


def validate_schema_config(schema: dict[str, Any], config: dict[str, Any] | None) -> list[str]:
    """Validate config data against schema types."""
    errors: list[str] = []
    if config is None:
        return errors
    if not isinstance(config, dict):
        return ["config must be an object"]
    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        value_type = spec.get("type")
        if key not in config:
            continue
        value = config.get(key)
        path = key
        if value_type == "object":
            if not isinstance(value, dict):
                errors.append(f"{path} must be an object")
            else:
                errors.extend(_prefix_errors(validate_schema_config(spec.get("items", {}), value), path))
            continue
        if value_type in ("list", "template_list"):
            if not isinstance(value, list):
                errors.append(f"{path} must be a list")
            continue
        if value_type == "bool":
            if not isinstance(value, bool):
                errors.append(f"{path} must be a bool")
            continue
        if value_type == "int":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{path} must be an int")
            continue
        if value_type == "float":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{path} must be a float")
            continue
        if value_type in ("string", "text"):
            if not isinstance(value, str):
                errors.append(f"{path} must be a string")
            continue

    return errors


def _schema_default(spec: dict[str, Any]) -> Any:
    if "default" in spec:
        return spec.get("default")
    value_type = spec.get("type")
    if value_type == "object":
        return {}
    if value_type in _DEFAULT_SCHEMA_VALUES:
        return _DEFAULT_SCHEMA_VALUES[value_type]
    return None


def _copy_default(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return copy.deepcopy(value)
    return value


def _prefix_errors(errors: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{error}" for error in errors]
