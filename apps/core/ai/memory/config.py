"""Memory configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ...config.file_utils import load_config_data, resolve_config_path
from ...config.loader import get_data_dir
from .config_models import (
    MemoryAssociationConfig,
    MemoryCompressionConfig,
    MemoryConfig,
    MemoryContextConfig,
    MemoryDreamingConfig,
    MemoryKGConfig,
    MemoryLayerStoreConfig,
    MemoryPipelineConfig,
    MemoryRecallConfig,
    MemoryRerankConfig,
    MemoryScoringConfig,
    MemorySparseConfig,
    MemoryStoreConfig,
    MemoryTimeConfig,
    MemoryVectorConfig,
)
from .time_utils import set_default_timezone


def _merge_dict(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def build_memory_config(data: dict[str, Any], *, defaults: MemoryConfig | None = None) -> MemoryConfig:
    base = defaults or MemoryConfig()
    merged = _merge_dict(defaults_to_dict(base), data)
    return MemoryConfig(
        time=MemoryTimeConfig(**merged.get("time", {})),
        store=MemoryStoreConfig(**merged.get("store", {})),
        l1_core=MemoryLayerStoreConfig(**merged.get("l1_core", {})),
        l2_semantic=MemoryLayerStoreConfig(**merged.get("l2_semantic", {})),
        l4_procedural=MemoryLayerStoreConfig(**merged.get("l4_procedural", {})),
        sparse=MemorySparseConfig(**merged.get("sparse", {})),
        vector=MemoryVectorConfig(**merged.get("vector", {})),
        kg=MemoryKGConfig(**merged.get("kg", {})),
        compression=MemoryCompressionConfig(**merged.get("compression", {})),
        context=MemoryContextConfig(**merged.get("context", {})),
        scoring=MemoryScoringConfig(**merged.get("scoring", {})),
        pipeline=MemoryPipelineConfig(**merged.get("pipeline", {})),
        recall=MemoryRecallConfig(**merged.get("recall", {})),
        rerank=MemoryRerankConfig(**merged.get("rerank", {})),
        association=MemoryAssociationConfig(**merged.get("association", {})),
        dreaming=MemoryDreamingConfig(**merged.get("dreaming", {})),
    )


def load_memory_config(path: str | Path | None = None) -> MemoryConfig:
    """Load memory configuration from yaml or toml."""
    if path is None:
        data_dir = get_data_dir()
        path = data_dir / "memory.yaml"
    path = resolve_config_path(Path(path))

    defaults = MemoryConfig()
    data: dict[str, Any] = load_config_data(path)

    config = build_memory_config(data, defaults=defaults)

    if not config.store.sqlite_path:
        config.store.sqlite_path = str(Path(get_data_dir()) / "memory" / "memory.db")
    if not config.store.state_path:
        config.store.state_path = str(Path(get_data_dir()) / "memory" / "state.json")
    if not config.vector.persist_path:
        config.vector.persist_path = str(Path(get_data_dir()) / "memory" / "vectors")

    _apply_layer_defaults(config)
    set_default_timezone(config.time.timezone)

    return config


def save_memory_config(config: MemoryConfig, path: str | Path | None = None) -> None:
    """Save memory configuration to yaml."""
    if path is None:
        path = Path(get_data_dir()) / "memory.yaml"
    path = Path(path)
    data = defaults_to_dict(config)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)


def config_to_dict(config: MemoryConfig) -> dict[str, Any]:
    return defaults_to_dict(config)


def defaults_to_dict(config: MemoryConfig) -> dict[str, Any]:
    return {
        "time": config.time.__dict__,
        "store": config.store.__dict__,
        "l1_core": config.l1_core.__dict__,
        "l2_semantic": config.l2_semantic.__dict__,
        "l4_procedural": config.l4_procedural.__dict__,
        "sparse": config.sparse.__dict__,
        "vector": config.vector.__dict__,
        "kg": config.kg.__dict__,
        "compression": config.compression.__dict__,
        "context": config.context.__dict__,
        "scoring": config.scoring.__dict__,
        "pipeline": config.pipeline.__dict__,
        "recall": config.recall.__dict__,
        "rerank": config.rerank.__dict__,
        "association": config.association.__dict__,
        "dreaming": config.dreaming.__dict__,
    }


def _apply_layer_defaults(config: MemoryConfig) -> None:
    data_dir = Path(get_data_dir()) / "memory"

    def apply_layer(layer: MemoryLayerStoreConfig, default_name: str) -> None:
        if not layer.sqlite_path:
            layer.sqlite_path = str(data_dir / f"{default_name}.db")
        if not layer.state_path:
            layer.state_path = str(data_dir / f"{default_name}.json")

    apply_layer(config.l1_core, "l1_core")
    apply_layer(config.l2_semantic, "l2_semantic")
    apply_layer(config.l4_procedural, "l4_procedural")
