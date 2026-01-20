"""
Memory layer store helpers.
"""

from __future__ import annotations

from .config import MemoryLayerStoreConfig
from .core_profile_state_store import CoreProfileStateStore
from .core_profile_store import CoreProfileStore
from .procedural_habits_state_store import ProceduralHabitsStateStore
from .procedural_habits_store import ProceduralHabitsStore
from .semantic_facts_state_store import SemanticFactsStateStore
from .semantic_facts_store import SemanticFactsStore


def build_core_profile_store(config: MemoryLayerStoreConfig) -> CoreProfileStore | CoreProfileStateStore | None:
    """Build core profile store based on config."""
    if not config.enabled:
        return None
    backend = (config.backend or "sqlite").lower()
    if backend == "state":
        return CoreProfileStateStore(config.state_path, max_records=config.max_records)
    if backend == "memory":
        return CoreProfileStateStore(None, max_records=config.max_records)
    return CoreProfileStore(config.sqlite_path, max_records=config.max_records)


def build_semantic_facts_store(config: MemoryLayerStoreConfig) -> SemanticFactsStore | SemanticFactsStateStore | None:
    """Build semantic facts store based on config."""
    if not config.enabled:
        return None
    backend = (config.backend or "sqlite").lower()
    if backend == "state":
        return SemanticFactsStateStore(config.state_path, max_records=config.max_records)
    if backend == "memory":
        return SemanticFactsStateStore(None, max_records=config.max_records)
    return SemanticFactsStore(config.sqlite_path, max_records=config.max_records)


def build_procedural_habits_store(
    config: MemoryLayerStoreConfig,
) -> ProceduralHabitsStore | ProceduralHabitsStateStore | None:
    """Build procedural habits store based on config."""
    if not config.enabled:
        return None
    backend = (config.backend or "sqlite").lower()
    if backend == "state":
        return ProceduralHabitsStateStore(config.state_path, max_records=config.max_records)
    if backend == "memory":
        return ProceduralHabitsStateStore(None, max_records=config.max_records)
    return ProceduralHabitsStore(config.sqlite_path, max_records=config.max_records)


__all__ = [
    "CoreProfileStore",
    "CoreProfileStateStore",
    "SemanticFactsStore",
    "SemanticFactsStateStore",
    "ProceduralHabitsStore",
    "ProceduralHabitsStateStore",
    "build_core_profile_store",
    "build_semantic_facts_store",
    "build_procedural_habits_store",
]
