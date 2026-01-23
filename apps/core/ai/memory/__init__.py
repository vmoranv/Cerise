"""
Memory module.
"""

from .config import (
    MemoryConfig,
    MemoryTimeConfig,
    build_memory_config,
    config_to_dict,
    load_memory_config,
    save_memory_config,
)
from .context_builder import MemoryContextBuilder
from .engine import MemoryEngine
from .extraction import CompositeMemoryExtractor, LLMMemoryExtractor, RuleBasedMemoryExtractor, build_memory_extractor
from .maintenance import MemoryMaintenance
from .pipeline import MemoryPipeline
from .registry import MemoryScorerRegistry
from .scorers import (
    EmotionImpactScorer,
    ImportanceScorer,
    KeywordOverlapScorer,
    RecencyScorer,
    ReinforcementScorer,
)
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
    "MemoryMaintenance",
    "RuleBasedMemoryExtractor",
    "LLMMemoryExtractor",
    "CompositeMemoryExtractor",
    "build_memory_extractor",
    "MemoryContextBuilder",
    "MemoryConfig",
    "MemoryTimeConfig",
    "build_memory_config",
    "config_to_dict",
    "load_memory_config",
    "save_memory_config",
    "MemoryScorerRegistry",
    "KeywordOverlapScorer",
    "RecencyScorer",
    "ImportanceScorer",
    "EmotionImpactScorer",
    "ReinforcementScorer",
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
