"""
Memory recall helpers.
"""

from __future__ import annotations

from datetime import datetime

from .compression import MemoryCompressor
from .config import MemoryConfig
from .retrieval import rrf_fuse
from .scorers import MemoryScorer
from .sqlite_store import SqliteKnowledgeGraphStore
from .store import MemoryStore
from .types import MemoryResult


class RecallMixin:
    config: MemoryConfig | None
    store: MemoryStore
    scorers: list[MemoryScorer]
    _retrievers: list
    _compressor: MemoryCompressor | None
    kg_store: SqliteKnowledgeGraphStore | None

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
