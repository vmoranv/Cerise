from pathlib import Path

import yaml
from apps.core.ai.memory import config as memory_config


def test_memory_layer_config_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(memory_config, "get_data_dir", lambda: tmp_path)

    config = memory_config.load_memory_config(path=tmp_path / "memory.yaml")

    assert config.l1_core.enabled is True
    assert config.l2_semantic.enabled is True
    assert config.l4_procedural.enabled is True
    assert config.l1_core.sqlite_path.endswith(str(Path("memory") / "l1_core.db"))
    assert config.l2_semantic.sqlite_path.endswith(str(Path("memory") / "l2_semantic.db"))
    assert config.l4_procedural.sqlite_path.endswith(str(Path("memory") / "l4_procedural.db"))


def test_memory_layer_config_overrides(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(memory_config, "get_data_dir", lambda: tmp_path)

    config_path = tmp_path / "memory.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "l1_core": {"enabled": False, "backend": "memory", "max_records": 12},
                "l2_semantic": {"backend": "state"},
                "l4_procedural": {"max_records": 5},
            }
        ),
        encoding="utf-8",
    )

    config = memory_config.load_memory_config(path=config_path)

    assert config.l1_core.enabled is False
    assert config.l1_core.backend == "memory"
    assert config.l1_core.max_records == 12
    assert config.l2_semantic.backend == "state"
    assert config.l4_procedural.max_records == 5
