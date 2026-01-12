"""
Memory retrieval pipeline with RRF fusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .sqlite_store import SqliteKnowledgeGraphStore
from .store import MemoryStore
from .types import MemoryRecord, MemoryResult
from .vector_index import Embedder, VectorIndex


class Retriever(Protocol):
    """Retriever protocol."""

    name: str

    async def retrieve(self, query: str, session_id: str | None, top_k: int) -> list[MemoryResult]:
        """Retrieve memory results."""


@dataclass
class BM25Retriever:
    """BM25 sparse retriever using SQLite FTS5 or fallback."""

    store: MemoryStore

    name: str = "bm25"

    async def retrieve(self, query: str, session_id: str | None, top_k: int) -> list[MemoryResult]:
        if hasattr(self.store, "supports_fts") and hasattr(self.store, "search_fts"):
            supports_fts = getattr(self.store, "supports_fts")
            search_fts = getattr(self.store, "search_fts")
            if callable(supports_fts) and callable(search_fts) and supports_fts():
                scored_ids = search_fts(query, session_id, top_k)
                results = []
                for record_id, score in scored_ids:
                    record = await self.store.get(record_id)
                    if record:
                        results.append(MemoryResult(record=record, score=score))
                return results

        # Fallback: keyword overlap
        records = await self.store.list(session_id=session_id)
        results = []
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return []
        for record in records:
            tokens = set(_tokenize(record.content))
            overlap = len(query_tokens & tokens)
            score = overlap / max(len(query_tokens), 1)
            if score > 0:
                results.append(MemoryResult(record=record, score=score))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]


@dataclass
class VectorRetriever:
    """Vector retriever using a vector index."""

    store: MemoryStore
    index: VectorIndex
    embedder: Embedder

    name: str = "vector"

    async def retrieve(self, query: str, session_id: str | None, top_k: int) -> list[MemoryResult]:
        if top_k <= 0:
            return []
        vector = (await self.embedder.embed([query]))[0]
        scored_ids = self.index.search(vector, top_k)
        results = []
        for record_id, score in scored_ids:
            record = await self.store.get(record_id)
            if record and (session_id is None or record.session_id == session_id):
                results.append(MemoryResult(record=record, score=score))
        return results


@dataclass
class KnowledgeGraphRetriever:
    """Knowledge graph retriever using stored triples."""

    store: SqliteKnowledgeGraphStore

    name: str = "kg"

    async def retrieve(self, query: str, session_id: str | None, top_k: int) -> list[MemoryResult]:
        triples = await self.store.search(query, session_id, top_k)
        results: list[MemoryResult] = []
        for triple in triples:
            content = f"Fact: {triple['subject']} {triple['predicate']} {triple['object']}"
            record = MemoryRecord(
                session_id=triple["session_id"],
                role="system",
                content=content,
                metadata={
                    "type": "kg",
                    "subject": triple["subject"],
                    "predicate": triple["predicate"],
                    "object": triple["object"],
                    "memory_id": triple.get("memory_id"),
                },
            )
            results.append(MemoryResult(record=record, score=triple["score"]))
        return results


def rrf_fuse(
    ranked_lists: list[list[MemoryResult]],
    *,
    k: int = 60,
) -> list[MemoryResult]:
    scores: dict[str, float] = {}
    records: dict[str, MemoryRecord] = {}

    for results in ranked_lists:
        for rank, item in enumerate(results, start=1):
            key = item.record.id
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            records[key] = item.record

    fused = [MemoryResult(record=records[key], score=score) for key, score in scores.items()]
    fused.sort(key=lambda item: item.score, reverse=True)
    return fused


def _tokenize(text: str) -> list[str]:
    tokens = []
    buf = ""
    for ch in text.lower():
        if ch.isalnum():
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            if "\u4e00" <= ch <= "\u9fff":
                tokens.append(ch)
    if buf:
        tokens.append(buf)
    return tokens
