"""Unit tests for plugin name validation."""

import pytest
from apps.core.plugins.name_safety import validate_plugin_name


def test_validate_plugin_name_accepts_safe_names() -> None:
    assert validate_plugin_name("echo-python") == "echo-python"
    assert validate_plugin_name("  echo-node  ") == "echo-node"


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        ".",
        "..",
        "a/b",
        "a\\b",
        "a:b",
    ],
)
def test_validate_plugin_name_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(ValueError):
        validate_plugin_name(name)
