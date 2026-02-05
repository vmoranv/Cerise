"""Unit tests for plugin directory resolution."""

from apps.core.api.container import _resolve_plugins_dir


def test_resolve_plugins_dir_prefers_repo_plugins_dir() -> None:
    plugins_dir = _resolve_plugins_dir()

    # In this repository, the runtime plugins live at repo-root/plugins.
    assert plugins_dir.name == "plugins"
    assert (plugins_dir / "web-search" / "manifest.json").exists()

    # Ensure we didn't accidentally choose the core implementation package dir.
    assert not (plugins_dir / "transport_stdio.py").exists()
