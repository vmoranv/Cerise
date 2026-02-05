"""Plugin name validation helpers.

These are used to prevent path traversal when plugin names are provided by users (e.g. admin API).
"""

from __future__ import annotations


def validate_plugin_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("Plugin name is required")
    if cleaned in {".", ".."}:
        raise ValueError("Invalid plugin name")
    if any(ch in cleaned for ch in ("/", "\\", ":")):
        raise ValueError("Invalid plugin name")
    return cleaned
