import json
from pathlib import Path

from apps.core.config.loader import ConfigLoader


def _write_schema(path: Path) -> dict:
    schema = {
        "enabled": {"type": "bool", "default": True},
        "settings": {
            "type": "object",
            "items": {
                "threshold": {"type": "int", "default": 3},
            },
        },
    }
    path.write_text(json.dumps(schema), encoding="utf-8")
    return schema


def test_star_config_defaults(tmp_path: Path) -> None:
    loader = ConfigLoader(tmp_path)
    plugin_dir = tmp_path / "plugins" / "demo"
    plugin_dir.mkdir(parents=True)
    schema = _write_schema(plugin_dir / "_conf_schema.json")

    config = loader.load_star_config("demo", schema=schema)
    assert config["enabled"] is True
    assert config["settings"]["threshold"] == 3
    assert loader.get_star_config_path("demo").exists()


def test_star_config_validation(tmp_path: Path) -> None:
    loader = ConfigLoader(tmp_path)
    plugin_dir = tmp_path / "plugins" / "demo"
    plugin_dir.mkdir(parents=True)
    schema = _write_schema(plugin_dir / "_conf_schema.json")

    bad_config = {"enabled": "no", "settings": {"threshold": "high"}}
    loader.save_star_config("demo", bad_config)

    errors = loader.validate_star_config(bad_config, schema)
    assert errors
