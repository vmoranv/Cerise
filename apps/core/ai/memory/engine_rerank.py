"""
Memory rerank helpers.
"""

from __future__ import annotations

import logging

from .config import MemoryConfig
from .types import MemoryResult
from .vector_index import Embedder

logger = logging.getLogger(__name__)


class RerankMixin:
    config: MemoryConfig | None
    embedder: Embedder | None

    async def _rerank_with_embeddings(self, query: str, candidates: list[MemoryResult]) -> list[float]:
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

    async def _rerank_with_provider(self, query: str, candidates: list[MemoryResult]) -> list[float]:
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
