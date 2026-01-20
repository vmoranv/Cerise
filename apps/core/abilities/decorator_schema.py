"""Schema helpers for decorators."""

from __future__ import annotations

import inspect
from collections.abc import Callable


def extract_description(docstring: str) -> str:
    """Extract description from docstring (first non-empty line)."""
    lines = docstring.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("Args:"):
            return line
    return ""


def extract_schema_from_signature(sig: inspect.Signature, func: Callable) -> dict:
    """Extract JSON Schema from function signature."""
    properties: dict[str, dict] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("params", "context", "self"):
            continue

        prop = {"type": "string"}

        if param.annotation != inspect.Parameter.empty:
            prop = python_type_to_json_schema(param.annotation)

        properties[param_name] = prop

        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def extract_schema_from_docstring(func: Callable) -> dict:
    """Extract JSON Schema from docstring Args section."""
    doc = func.__doc__ or ""
    sig = inspect.signature(func)

    properties: dict[str, dict] = {}
    required: list[str] = []

    in_args = False
    for line in doc.split("\n"):
        line = line.strip()
        if line.startswith("Args:"):
            in_args = True
            continue
        if in_args:
            if not line or line.startswith("Returns:"):
                break
            if ":" in line:
                parts = line.split(":", 1)
                param_part = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""

                if "(" in param_part:
                    name = param_part.split("(")[0].strip()
                    type_str = param_part.split("(")[1].rstrip(")")
                else:
                    name = param_part
                    type_str = "string"

                properties[name] = {
                    "type": docstring_type_to_json(type_str),
                    "description": desc,
                }
                required.append(name)

    if not properties:
        return extract_schema_from_signature(sig, func)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def python_type_to_json_schema(python_type: type) -> dict:
    """Convert Python type annotation to JSON Schema."""
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    return type_map.get(python_type, {"type": "string"})


def docstring_type_to_json(type_str: str) -> str:
    """Convert docstring type to JSON Schema type."""
    type_map = {
        "str": "string",
        "string": "string",
        "int": "integer",
        "integer": "integer",
        "float": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "list": "array",
        "array": "array",
        "dict": "object",
        "object": "object",
    }
    return type_map.get(type_str.lower(), "string")
