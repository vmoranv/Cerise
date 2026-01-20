"""
Memory ingestion helpers.
"""

from __future__ import annotations

import logging

from ...contracts.events import MEMORY_RECORDED, build_memory_recorded
from ...infrastructure import Event, EventBus
from .config import MemoryConfig
from .kg import extract_triples
from .sqlite_store import SqliteKnowledgeGraphStore
from .store import MemoryStore
from .types import MemoryRecord
from .vector_index import Embedder, VectorIndex

logger = logging.getLogger(__name__)


class IngestMixin:
    config: MemoryConfig | None
    store: MemoryStore
    vector_index: VectorIndex | None
    embedder: Embedder | None
    kg_store: SqliteKnowledgeGraphStore | None
    bus: EventBus | None

    async def add_record(self, record: MemoryRecord) -> None:
        expires_at = None
        if self.config and self.config.store.ttl_seconds > 0:
            expires_at = record.created_at.timestamp() + self.config.store.ttl_seconds
        await self.store.add(record, expires_at=expires_at)

        if self.vector_index and self.embedder:
            try:
                vector = (await self.embedder.embed([record.content]))[0]
                self.vector_index.add([record.id], [vector])
            except Exception:
                logger.exception("Embedding failed for record %s", record.id)

        if self.kg_store and self.config and self.config.kg.auto_extract:
            triples = extract_triples(record.content)
            await self.kg_store.add_triples(record.session_id, triples, memory_id=record.id)

        await self._enforce_session_limits(record.session_id)
        await self._maybe_compress(record.session_id)

        if self.bus:
            self.bus.publish_sync(
                Event(
                    type=MEMORY_RECORDED,
                    data=build_memory_recorded(record.id, record.session_id),
                    source="memory_engine",
                )
            )

    async def ingest_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        await self.add_record(record)
        return record
