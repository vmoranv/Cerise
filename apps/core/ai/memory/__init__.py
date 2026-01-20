"""
Memory module.
"""

from .config import MemoryConfig, load_memory_config
from .engine import MemoryEngine
from .pipeline import MemoryPipeline, RuleBasedMemoryExtractor
from .registry import MemoryScorerRegistry
from .scorers import KeywordOverlapScorer, RecencyScorer
from .sqlite_store import SqliteMemoryStore
from .store import InMemoryStore, MemoryStore, StateStoreMemoryStore
from .types import (
    CoreProfile,
    MemoryLayer,
    MemoryRecord,
    MemoryResult,
    MemoryType,
    ProceduralHabit,
    SemanticFact,
)


def __getattr__(name: str):
    if name == "MemoryEventHandler":
        from .events import MemoryEventHandler

        return MemoryEventHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MemoryEngine",
    "MemoryEventHandler",
    "MemoryPipeline",
    "RuleBasedMemoryExtractor",
    "MemoryConfig",
    "load_memory_config",
    "MemoryScorerRegistry",
    "KeywordOverlapScorer",
    "RecencyScorer",
    "InMemoryStore",
    "MemoryStore",
    "StateStoreMemoryStore",
    "SqliteMemoryStore",
    "MemoryLayer",
    "MemoryType",
    "MemoryRecord",
    "MemoryResult",
    "CoreProfile",
    "SemanticFact",
    "ProceduralHabit",
]
