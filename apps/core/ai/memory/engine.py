"""
Memory engine for ingestion and recall.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ...infrastructure import EventBus
from .config import MemoryConfig, load_memory_config
from .engine_association import AssociationMixin
from .engine_build import BuildMixin
from .engine_ingest import IngestMixin
from .engine_recall import RecallMixin
from .engine_rerank import RerankMixin
from .maintenance import MemoryMaintenance
from .registry import MemoryScorerRegistry
from .scorers import MemoryScorer
from .sqlite_store import SqliteKnowledgeGraphStore
from .store import MemoryStore
from .vector_index import Embedder, VectorIndex


@dataclass
class MemoryEngine(BuildMixin, IngestMixin, RecallMixin, AssociationMixin, RerankMixin):
    """Event-driven memory engine with hybrid retrieval."""

    store: MemoryStore
    scorers: Iterable[MemoryScorer]
    bus: EventBus | None = None
    config: MemoryConfig | None = None
    embedder: Embedder | None = None
    vector_index: VectorIndex | None = None
    kg_store: SqliteKnowledgeGraphStore | None = None

    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        scorers: list[MemoryScorer] | None = None,
        registry: MemoryScorerRegistry | None = None,
        bus: EventBus | None = None,
        config: MemoryConfig | None = None,
        embedder: Embedder | None = None,
        vector_index: VectorIndex | None = None,
    ):
        self.config = config or load_memory_config()
        self.store = store or self._build_store(self.config)
        if scorers is None:
            registry = registry or MemoryScorerRegistry.default(self.config)
            scorers = registry.build()
        self.scorers = list(scorers)
        self.bus = bus
        self.embedder = embedder or self._build_embedder(self.config)
        self.vector_index = vector_index or self._build_vector_index(self.config)
        self.kg_store = self._build_kg_store(self.config)
        self._retrievers = self._build_retrievers(self.config)
        self._compressor = self._build_compressor(self.config)
        self._vector_loaded = False

    async def run_maintenance(self, *, session_id: str | None = None) -> dict[str, int]:
        if not self.config:
            return {"updated": 0, "deleted": 0}
        maint = MemoryMaintenance(store=self.store, config=self.config)
        return await maint.run(session_id=session_id)
