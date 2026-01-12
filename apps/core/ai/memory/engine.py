"""
Memory engine for ingestion and recall.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from ...config.loader import get_data_dir
from ...infrastructure import Event, MessageBus
from .compression import MemoryCompressor
from .config import MemoryConfig, load_memory_config
from .kg import extract_entities, extract_triples
from .registry import MemoryScorerRegistry
from .retrieval import BM25Retriever, KnowledgeGraphRetriever, VectorRetriever, rrf_fuse
from .scorers import MemoryScorer
from .sqlite_store import SqliteKnowledgeGraphStore, SqliteMemoryStore
from .store import InMemoryStore, MemoryStore, StateStoreMemoryStore
from .types import MemoryRecord, MemoryResult
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


@dataclass
class MemoryEngine:
    """Event-driven memory engine with hybrid retrieval."""

    store: MemoryStore
    scorers: Iterable[MemoryScorer]
    bus: MessageBus | None = None
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
        bus: MessageBus | None = None,
        config: MemoryConfig | None = None,
        embedder: Embedder | None = None,
        vector_index: VectorIndex | None = None,
    ):
        self.config = config or load_memory_config()
        self.store = store or self._build_store(self.config)
        if scorers is None:
            registry = registry or MemoryScorerRegistry.default()
            scorers = registry.build()
        self.scorers = list(scorers)
        self.bus = bus
        self.embedder = embedder or self._build_embedder(self.config)
        self.vector_index = vector_index or self._build_vector_index(self.config)
        self.kg_store = self._build_kg_store(self.config)
        self._retrievers = self._build_retrievers(self.config)
        self._compressor = self._build_compressor(self.config)
        self._vector_loaded = False

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
        return MemoryCompressor(
            threshold=config.compression.threshold,
            window=config.compression.window,
            max_chars=config.compression.max_chars,
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
                    type="memory.recorded",
                    data={"record_id": record.id, "session_id": record.session_id},
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

    async def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        session_id: str | None = None,
    ) -> list[MemoryResult]:
        if not self.config or not self.config.recall.enabled:
            return []
        ranked_lists = []
        for retriever in self._retrievers:
            top_k = self._retriever_top_k(retriever)
            results = await retriever.retrieve(query, session_id, top_k)
            ranked_lists.append(results)
        fused = rrf_fuse(ranked_lists, k=self.config.recall.rrf_k)

        assoc_results: list[MemoryResult] = []
        if self.config.association.enabled and self.kg_store:
            assoc_results = await self._associative_recall(query, fused, session_id)
            if assoc_results:
                fused = rrf_fuse([fused, assoc_results], k=self.config.recall.rrf_k)

        min_score = self.config.recall.min_score
        if self.config.association.enabled:
            min_score = min(min_score, self.config.association.min_score)
        filtered = self._filter_results(fused, min_score)
        rescored = self._apply_scorers(query, filtered)
        reranked = await self._rerank_results(query, rescored)
        reranked.sort(key=lambda item: item.score, reverse=True)
        filled = await self._fill_with_recent(reranked, limit, session_id)
        return filled[:limit]

    def format_context(self, results: list[MemoryResult]) -> str:
        """Format memory results for prompt injection."""
        if not results:
            return ""
        lines = ["[Memory Recall]"]
        for idx, item in enumerate(results, start=1):
            record = item.record
            content = " ".join(record.content.split())
            if len(content) > 200:
                content = content[:197].rstrip() + "..."
            timestamp = record.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"{idx}. ({record.role} @ {timestamp}) {content}")
        return "\n".join(lines)

    def _retriever_top_k(self, retriever) -> int:
        if retriever.name == "vector" and self.config:
            return self.config.vector.top_k
        if retriever.name == "bm25" and self.config:
            return self.config.sparse.top_k
        if retriever.name == "kg" and self.config:
            return self.config.kg.top_k
        return self.config.recall.top_k if self.config else 5

    def _filter_results(self, results: list[MemoryResult], min_score: float) -> list[MemoryResult]:
        filtered: list[MemoryResult] = []
        seen: set[str] = set()
        seen_ids: set[str] = set()
        for item in results:
            if item.score < min_score:
                continue
            if item.record.id in seen_ids:
                continue
            seen_ids.add(item.record.id)
            key = item.record.content.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            filtered.append(item)
        return filtered

    def _apply_scorers(self, query: str, results: list[MemoryResult]) -> list[MemoryResult]:
        if not self.scorers:
            return results
        scorer_count = len(self.scorers)
        rescored: list[MemoryResult] = []
        for item in results:
            score = item.score
            bonus = 0.0
            for scorer in self.scorers:
                bonus += scorer.score(query, item.record)
            if scorer_count:
                bonus /= scorer_count
            rescored.append(MemoryResult(record=item.record, score=score + bonus))
        return rescored

    async def _rerank_results(self, query: str, results: list[MemoryResult]) -> list[MemoryResult]:
        if not self.config or not self.config.rerank.enabled:
            return results
        if not results:
            return results
        top_k = self.config.rerank.top_k
        if top_k <= 0:
            return results
        top_k = min(top_k, len(results))
        candidates = results[:top_k]
        tail = results[top_k:]

        rerank_scores = await self._rerank_with_provider(query, candidates)
        if not rerank_scores:
            rerank_scores = await self._rerank_with_embeddings(query, candidates)
        if not rerank_scores:
            return results

        weight = self.config.rerank.weight
        merged: list[MemoryResult] = []
        for item, score in zip(candidates, rerank_scores):
            blended = (1.0 - weight) * item.score + weight * score
            merged.append(MemoryResult(record=item.record, score=blended))
        merged.sort(key=lambda item: item.score, reverse=True)
        return merged + tail

    async def _enforce_session_limits(self, session_id: str) -> None:
        if not self.config:
            return
        limit = self.config.store.max_records_per_session
        if limit <= 0:
            return
        count = await self.store.count(session_id=session_id)
        if count <= limit:
            return
        records = await self.store.list(session_id=session_id)
        overflow = max(0, len(records) - limit)
        if overflow <= 0:
            return
        delete_ids = [record.id for record in records[:overflow]]
        await self.store.delete(delete_ids)

    async def _maybe_compress(self, session_id: str) -> None:
        if not self._compressor:
            return
        count = await self.store.count(session_id=session_id)
        if not self._compressor.should_compress(count):
            return
        records = await self.store.list(session_id=session_id)
        to_compress = self._compressor.select_records(records)
        if not to_compress:
            return
        summary = self._compressor.compress(to_compress)
        await self.store.delete([record.id for record in to_compress])
        await self.store.add(summary, expires_at=self._summary_expiry())

    def _summary_expiry(self) -> float | None:
        if not self.config or self.config.store.ttl_seconds <= 0:
            return None
        return datetime.utcnow().timestamp() + self.config.store.ttl_seconds

    async def _associative_recall(
        self,
        query: str,
        base_results: list[MemoryResult],
        session_id: str | None,
    ) -> list[MemoryResult]:
        if not self.config or not self.kg_store:
            return []
        cfg = self.config.association
        if cfg.max_hops <= 0:
            return []
        entities = self._gather_entities(
            query, base_results, cfg.max_entities, cfg.expand_from_query, cfg.expand_from_results
        )
        if not entities:
            return []

        all_results: list[MemoryResult] = []
        seen_entities = set(entities)
        hop_entities = entities
        for _ in range(cfg.max_hops):
            triples = await self.kg_store.search_related(hop_entities, session_id, cfg.top_k)
            if not triples:
                break
            hop_results, extra_entities = await self._triples_to_results(triples, cfg.include_facts)
            all_results.extend(hop_results)
            new_entities = [entity for entity in extra_entities if entity not in seen_entities]
            if not new_entities:
                break
            seen_entities.update(new_entities)
            hop_entities = new_entities[: cfg.max_entities]
        return all_results

    def _gather_entities(
        self,
        query: str,
        base_results: list[MemoryResult],
        max_entities: int,
        expand_from_query: bool,
        expand_from_results: bool,
    ) -> list[str]:
        entities: list[str] = []
        if expand_from_query:
            entities.extend(extract_entities(query, max_entities=max_entities))
        if expand_from_results:
            for item in base_results[: min(len(base_results), 5)]:
                if len(entities) >= max_entities:
                    break
                more = extract_entities(item.record.content, max_entities=max_entities - len(entities))
                entities.extend(more)
        deduped: list[str] = []
        seen = set()
        for entity in entities:
            if entity in seen:
                continue
            seen.add(entity)
            deduped.append(entity)
            if len(deduped) >= max_entities:
                break
        return deduped

    async def _triples_to_results(
        self,
        triples: list[dict],
        include_facts: bool,
    ) -> tuple[list[MemoryResult], list[str]]:
        results: list[MemoryResult] = []
        entities: list[str] = []
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            if subject:
                entities.append(subject)
            if obj:
                entities.append(obj)
            memory_id = triple.get("memory_id")
            if memory_id:
                record = await self.store.get(memory_id)
                if record:
                    results.append(MemoryResult(record=record, score=float(triple.get("score", 0.3)) + 0.2))
            if include_facts:
                content = f"Fact: {subject} {triple.get('predicate', '')} {obj}".strip()
                record = MemoryRecord(
                    session_id=triple.get("session_id", ""),
                    role="system",
                    content=content,
                    metadata={
                        "type": "kg",
                        "subject": subject,
                        "predicate": triple.get("predicate", ""),
                        "object": obj,
                        "memory_id": memory_id,
                    },
                )
                results.append(MemoryResult(record=record, score=float(triple.get("score", 0.3))))
        return results, entities

    async def _fill_with_recent(
        self,
        results: list[MemoryResult],
        limit: int,
        session_id: str | None,
    ) -> list[MemoryResult]:
        if len(results) >= limit:
            return results
        records = await self.store.list(session_id=session_id)
        records.sort(key=lambda record: record.created_at, reverse=True)
        seen_ids = {item.record.id for item in results}
        for record in records:
            if len(results) >= limit:
                break
            if record.id in seen_ids:
                continue
            results.append(MemoryResult(record=record, score=0.01))
            seen_ids.add(record.id)
        return results

    async def _rerank_with_embeddings(
        self,
        query: str,
        candidates: list[MemoryResult],
    ) -> list[float]:
        if not self.embedder:
            return []
        texts = [query] + [item.record.content for item in candidates]
        try:
            vectors = await self.embedder.embed(texts)
        except Exception:
            logger.exception("Embedding rerank failed")
            return []
        if len(vectors) != len(texts):
            return []
        query_vec = vectors[0]
        doc_vecs = vectors[1:]
        return [self._cosine_similarity(query_vec, vec) for vec in doc_vecs]

    async def _rerank_with_provider(
        self,
        query: str,
        candidates: list[MemoryResult],
    ) -> list[float]:
        if not self.config:
            return []
        provider_id = self.config.rerank.provider_id
        if not provider_id:
            return []
        from ..providers import ProviderRegistry

        provider = ProviderRegistry.get(provider_id)
        if not provider:
            return []
        if not provider.get_capabilities().rerank:
            return []
        docs = [item.record.content for item in candidates]
        try:
            results = await provider.rerank(
                query=query,
                documents=docs,
                model=self.config.rerank.model or None,
                top_k=len(docs),
            )
        except Exception:
            logger.exception("Provider rerank failed")
            return []
        scores = [0.0] * len(docs)
        for idx, score in results:
            if 0 <= idx < len(scores):
                scores[idx] = float(score)
        return scores

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for a, b in zip(vec_a, vec_b):
            dot += a * b
            norm_a += a * a
            norm_b += b * b
        if norm_a <= 0 or norm_b <= 0:
            return 0.0
        return dot / ((norm_a**0.5) * (norm_b**0.5))
