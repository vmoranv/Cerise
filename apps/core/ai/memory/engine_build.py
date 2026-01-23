"""
Memory engine build helpers.
"""

from __future__ import annotations

import logging

from ...config.loader import get_data_dir
from .compression import MemoryCompressor, ProviderSummaryProvider
from .config import MemoryConfig
from .retrieval import BM25Retriever, KnowledgeGraphRetriever, VectorRetriever
from .sqlite_store import SqliteKnowledgeGraphStore, SqliteMemoryStore
from .store import InMemoryStore, MemoryStore, StateStoreMemoryStore
from .vector_index import (
    ChromaVectorIndex,
    Embedder,
    FaissVectorIndex,
    HashEmbedder,
    NumpyVectorIndex,
    ProviderEmbedder,
    VectorIndex,
)

logger = logging.getLogger(__name__)


class BuildMixin:
    store: MemoryStore
    embedder: Embedder | None
    vector_index: VectorIndex | None
    kg_store: SqliteKnowledgeGraphStore | None
    config: MemoryConfig | None
    _retrievers: list
    _compressor: MemoryCompressor | None
    _vector_loaded: bool

    def _build_store(self, config: MemoryConfig) -> MemoryStore:
        backend = (config.store.backend or "sqlite").lower()
        if backend == "state":
            return StateStoreMemoryStore(config.store.state_path)
        if backend == "memory":
            return InMemoryStore(max_records=config.store.max_records_per_session * 5)
        return SqliteMemoryStore(config.store.sqlite_path)

    def _build_embedder(self, config: MemoryConfig) -> Embedder | None:
        if not config.vector.enabled:
            return None
        backend = (config.vector.embedding_backend or "hash").lower()
        if backend == "hash":
            return HashEmbedder(dim=config.vector.embedding_dim)
        if backend in {"provider", "external"}:
            provider_id = config.vector.embedding_provider or None
            embedder = ProviderEmbedder(provider_id=provider_id, model=config.vector.embedding_model or None)
            return embedder
        logger.warning("Embedding backend '%s' not available, using hash fallback.", config.vector.embedding_backend)
        return HashEmbedder(dim=config.vector.embedding_dim)

    def _build_vector_index(self, config: MemoryConfig) -> VectorIndex | None:
        if not config.vector.enabled:
            return None
        provider = (config.vector.provider or "numpy").lower()
        if provider == "faiss":
            try:
                return FaissVectorIndex(config.vector.embedding_dim)
            except RuntimeError as exc:
                logger.warning("Faiss unavailable: %s. Falling back to numpy index.", exc)
        if provider == "chroma":
            try:
                return ChromaVectorIndex(config.vector.embedding_dim, config.vector.persist_path)
            except RuntimeError as exc:
                logger.warning("Chroma unavailable: %s. Falling back to numpy index.", exc)
        return NumpyVectorIndex(config.vector.embedding_dim)

    def _build_kg_store(self, config: MemoryConfig) -> SqliteKnowledgeGraphStore | None:
        if not config.kg.enabled:
            return None
        sqlite_path = config.store.sqlite_path or str(get_data_dir() / "memory" / "memory.db")
        return SqliteKnowledgeGraphStore(sqlite_path)

    def _build_retrievers(self, config: MemoryConfig) -> list:
        retrievers = []
        if config.sparse.enabled:
            retrievers.append(BM25Retriever(store=self.store))
        if config.vector.enabled and self.vector_index and self.embedder:
            retrievers.append(VectorRetriever(store=self.store, index=self.vector_index, embedder=self.embedder))
        if config.kg.enabled and self.kg_store:
            retrievers.append(KnowledgeGraphRetriever(store=self.kg_store))
        return retrievers

    def _build_compressor(self, config: MemoryConfig) -> MemoryCompressor | None:
        if not config.compression.enabled:
            return None
        summary_provider = None
        if config.compression.summary_provider_id:
            summary_provider = ProviderSummaryProvider(
                provider_id=config.compression.summary_provider_id,
                model=config.compression.summary_model or None,
                temperature=config.compression.summary_temperature,
                max_tokens=config.compression.summary_max_tokens,
            )
        return MemoryCompressor(
            threshold=config.compression.threshold,
            window=config.compression.window,
            max_chars=config.compression.max_chars,
            summary_provider=summary_provider,
        )

    async def prepare(self) -> None:
        """Warm up indexes for persistent memory."""
        if self.vector_index and self.embedder and not self._vector_loaded:
            await self._rebuild_vector_index()
        self._vector_loaded = True

    async def _rebuild_vector_index(self) -> None:
        records = await self.store.list()
        if not records:
            return
        texts = [record.content for record in records]
        vectors = await self.embedder.embed(texts) if self.embedder else []
        ids = [record.id for record in records]
        if vectors and self.vector_index:
            self.vector_index.add(ids, vectors)
