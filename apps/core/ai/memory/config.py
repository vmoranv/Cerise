"""
Memory configuration loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ...config.file_utils import load_config_data, resolve_config_path
from ...config.loader import get_data_dir
from .time_utils import set_default_timezone


@dataclass
class MemoryStoreConfig:
    """Storage configuration."""

    backend: str = "sqlite"  # sqlite | state | memory
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
    summary_provider_id: str = ""
    summary_model: str = ""
    summary_temperature: float = 0.2
    summary_max_tokens: int = 400


@dataclass
class MemoryTimeConfig:
    """Time and formatting configuration."""

    timezone: str = "UTC"
    timestamp_format: str = "%Y-%m-%d %H:%M"


@dataclass
class MemoryContextConfig:
    """Context assembly configuration."""

    enabled: bool = True
    max_items: int = 12
    layer_weights: dict[str, float] = field(
        default_factory=lambda: {
            "core": 1.0,
            "semantic": 1.0,
            "procedural": 1.0,
            "episodic": 2.0,
        }
    )
    max_per_layer: dict[str, int] = field(default_factory=dict)
    include_tags: bool = True
    include_category: bool = True
    include_emotion: bool = True
    include_scores: bool = False


@dataclass
class MemoryScoringConfig:
    """Scoring configuration."""

    recency_half_life_seconds: int = 1800
    recency_weight: float = 1.0
    importance_weight: float = 0.15
    emotional_weight: float = 0.1
    reinforcement_weight: float = 0.05
    max_access_count: int = 20
    emotion_filter_enabled: bool = False
    emotion_min_intensity: float = 0.2


@dataclass
class MemoryPipelineConfig:
    """Extraction pipeline configuration."""

    extractor: str = "rule"  # rule | llm | composite
    llm_provider_id: str = ""
    llm_model: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 800
    emotion_on_ingest: bool = True
    task_type_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class MemoryDreamingConfig:
    """Background maintenance configuration."""

    enabled: bool = False
    max_records: int = 200
    decay_half_life_seconds: int = 86400
    min_importance: float = 0.1
    prune_score_threshold: float = 0.05


@dataclass
class MemoryRecallConfig:
    """Recall configuration."""

    enabled: bool = True
    top_k: int = 8
    min_score: float = 0.05
    rrf_k: int = 60
    touch_on_recall: bool = True
    random_enabled: bool = False
    random_k: int = 1
    random_probability: float = 0.1
    trigger_keywords: list[str] = field(default_factory=lambda: ["random", "surprise", "想起", "突然想到"])


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

    time: MemoryTimeConfig = field(default_factory=MemoryTimeConfig)
    store: MemoryStoreConfig = field(default_factory=MemoryStoreConfig)
    l1_core: MemoryLayerStoreConfig = field(default_factory=MemoryLayerStoreConfig)
    l2_semantic: MemoryLayerStoreConfig = field(default_factory=MemoryLayerStoreConfig)
    l4_procedural: MemoryLayerStoreConfig = field(default_factory=MemoryLayerStoreConfig)
    sparse: MemorySparseConfig = field(default_factory=MemorySparseConfig)
    vector: MemoryVectorConfig = field(default_factory=MemoryVectorConfig)
    kg: MemoryKGConfig = field(default_factory=MemoryKGConfig)
    compression: MemoryCompressionConfig = field(default_factory=MemoryCompressionConfig)
    context: MemoryContextConfig = field(default_factory=MemoryContextConfig)
    scoring: MemoryScoringConfig = field(default_factory=MemoryScoringConfig)
    pipeline: MemoryPipelineConfig = field(default_factory=MemoryPipelineConfig)
    recall: MemoryRecallConfig = field(default_factory=MemoryRecallConfig)
    rerank: MemoryRerankConfig = field(default_factory=MemoryRerankConfig)
    association: MemoryAssociationConfig = field(default_factory=MemoryAssociationConfig)
    dreaming: MemoryDreamingConfig = field(default_factory=MemoryDreamingConfig)


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
