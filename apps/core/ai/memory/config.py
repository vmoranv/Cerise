"""
Memory configuration loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ...config.loader import get_data_dir


@dataclass
class MemoryStoreConfig:
    """Storage configuration."""

    backend: str = "sqlite"  # sqlite | state
    sqlite_path: str = ""
    state_path: str = ""
    ttl_seconds: int = 0
    max_records_per_session: int = 200


@dataclass
class MemoryVectorConfig:
    """Vector retrieval configuration."""

    enabled: bool = True
    provider: str = "faiss"  # faiss | chroma | numpy
    embedding_backend: str = "hash"  # hash | provider
    embedding_dim: int = 256
    embedding_provider: str = ""
    embedding_model: str = ""
    top_k: int = 5
    persist_path: str = ""


@dataclass
class MemorySparseConfig:
    """Sparse retrieval configuration."""

    enabled: bool = True
    top_k: int = 5


@dataclass
class MemoryKGConfig:
    """Knowledge graph configuration."""

    enabled: bool = True
    top_k: int = 3
    auto_extract: bool = True


@dataclass
class MemoryCompressionConfig:
    """Compression configuration."""

    enabled: bool = True
    threshold: int = 80
    window: int = 40
    max_chars: int = 1000


@dataclass
class MemoryRecallConfig:
    """Recall configuration."""

    enabled: bool = True
    top_k: int = 8
    min_score: float = 0.05
    rrf_k: int = 60


@dataclass
class MemoryRerankConfig:
    """Rerank configuration."""

    enabled: bool = True
    top_k: int = 8
    weight: float = 0.35
    provider_id: str = ""
    model: str = ""


@dataclass
class MemoryAssociationConfig:
    """Associative recall configuration."""

    enabled: bool = True
    max_hops: int = 1
    top_k: int = 5
    max_entities: int = 12
    include_facts: bool = True
    expand_from_query: bool = True
    expand_from_results: bool = True
    min_score: float = 0.02


@dataclass
class MemoryLayerStoreConfig:
    """Layered store configuration."""

    enabled: bool = True
    backend: str = "sqlite"  # sqlite | state | memory
    sqlite_path: str = ""
    state_path: str = ""
    max_records: int = 200


@dataclass
class MemoryConfig:
    """Overall memory configuration."""

    store: MemoryStoreConfig = field(default_factory=MemoryStoreConfig)
    l1_core: MemoryLayerStoreConfig = field(default_factory=MemoryLayerStoreConfig)
    l2_semantic: MemoryLayerStoreConfig = field(default_factory=MemoryLayerStoreConfig)
    l4_procedural: MemoryLayerStoreConfig = field(default_factory=MemoryLayerStoreConfig)
    sparse: MemorySparseConfig = field(default_factory=MemorySparseConfig)
    vector: MemoryVectorConfig = field(default_factory=MemoryVectorConfig)
    kg: MemoryKGConfig = field(default_factory=MemoryKGConfig)
    compression: MemoryCompressionConfig = field(default_factory=MemoryCompressionConfig)
    recall: MemoryRecallConfig = field(default_factory=MemoryRecallConfig)
    rerank: MemoryRerankConfig = field(default_factory=MemoryRerankConfig)
    association: MemoryAssociationConfig = field(default_factory=MemoryAssociationConfig)


def _merge_dict(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_memory_config(path: str | Path | None = None) -> MemoryConfig:
    """Load memory configuration from yaml."""
    if path is None:
        data_dir = get_data_dir()
        path = data_dir / "memory.yaml"
    path = Path(path)

    defaults = MemoryConfig()
    data: dict[str, Any] = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    merged = _merge_dict(defaults_to_dict(defaults), data)
    config = MemoryConfig(
        store=MemoryStoreConfig(**merged.get("store", {})),
        l1_core=MemoryLayerStoreConfig(**merged.get("l1_core", {})),
        l2_semantic=MemoryLayerStoreConfig(**merged.get("l2_semantic", {})),
        l4_procedural=MemoryLayerStoreConfig(**merged.get("l4_procedural", {})),
        sparse=MemorySparseConfig(**merged.get("sparse", {})),
        vector=MemoryVectorConfig(**merged.get("vector", {})),
        kg=MemoryKGConfig(**merged.get("kg", {})),
        compression=MemoryCompressionConfig(**merged.get("compression", {})),
        recall=MemoryRecallConfig(**merged.get("recall", {})),
        rerank=MemoryRerankConfig(**merged.get("rerank", {})),
        association=MemoryAssociationConfig(**merged.get("association", {})),
    )

    if not config.store.sqlite_path:
        config.store.sqlite_path = str(Path(get_data_dir()) / "memory" / "memory.db")
    if not config.store.state_path:
        config.store.state_path = str(Path(get_data_dir()) / "memory" / "state.json")
    if not config.vector.persist_path:
        config.vector.persist_path = str(Path(get_data_dir()) / "memory" / "vectors")

    _apply_layer_defaults(config)

    return config


def defaults_to_dict(config: MemoryConfig) -> dict[str, Any]:
    return {
        "store": config.store.__dict__,
        "l1_core": config.l1_core.__dict__,
        "l2_semantic": config.l2_semantic.__dict__,
        "l4_procedural": config.l4_procedural.__dict__,
        "sparse": config.sparse.__dict__,
        "vector": config.vector.__dict__,
        "kg": config.kg.__dict__,
        "compression": config.compression.__dict__,
        "recall": config.recall.__dict__,
        "rerank": config.rerank.__dict__,
        "association": config.association.__dict__,
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
