"""
Vector index and embedder implementations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """Embedding interface."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts into vectors."""


class VectorIndex(Protocol):
    """Vector index interface."""

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        """Add vectors to the index."""

    def search(self, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        """Search for nearest vectors."""


@dataclass
class HashEmbedder:
    """Deterministic hash-based embedder (fallback)."""

    dim: int = 256

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            for token in self._tokenize(text):
                idx = hash(token) % self.dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec.tolist())
        return vectors

    def _tokenize(self, text: str) -> list[str]:
        return [t for t in re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", text.lower()) if t]


@dataclass
class ProviderEmbedder:
    """Embedding provider wrapper."""

    provider_id: str | None = None
    model: str | None = None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from ..providers import ProviderRegistry

        provider = ProviderRegistry.get(self.provider_id) if self.provider_id else ProviderRegistry.get_default()
        if not provider:
            raise RuntimeError("No embedding provider available")
        capabilities = provider.get_capabilities()
        if not capabilities.embeddings:
            raise RuntimeError("Selected provider does not support embeddings")
        return await provider.embed(texts, model=self.model)


@dataclass
class NumpyVectorIndex:
    """In-memory cosine similarity index."""

    dim: int

    def __post_init__(self) -> None:
        self._ids: list[str] = []
        self._vectors = np.zeros((0, self.dim), dtype=np.float32)

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        if not ids:
            return
        array = np.array(vectors, dtype=np.float32)
        if array.shape[1] != self.dim:
            raise ValueError("Vector dimension mismatch")
        self._vectors = np.vstack([self._vectors, array])
        self._ids.extend(ids)

    def search(self, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        if not self._ids:
            return []
        query = np.array(vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []
        query = query / query_norm
        vecs = self._vectors
        norms = np.linalg.norm(vecs, axis=1)
        norms[norms == 0] = 1.0
        sims = (vecs @ query) / norms
        top_k = min(top_k, len(self._ids))
        indices = np.argpartition(-sims, top_k - 1)[:top_k]
        results = sorted(
            [(self._ids[i], float(sims[i])) for i in indices],
            key=lambda item: item[1],
            reverse=True,
        )
        return results


class FaissVectorIndex:
    """Faiss vector index wrapper."""

    def __init__(self, dim: int):
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError("faiss is not installed") from exc
        self._faiss = faiss
        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)
        self._ids: list[str] = []

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        if not ids:
            return
        array = np.array(vectors, dtype=np.float32)
        self._index.add(array)
        self._ids.extend(ids)

    def search(self, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        if not self._ids:
            return []
        query = np.array([vector], dtype=np.float32)
        scores, indices = self._index.search(query, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._ids):
                continue
            results.append((self._ids[idx], float(score)))
        return results


class ChromaVectorIndex:
    """Chroma vector index wrapper."""

    def __init__(self, dim: int, path: str):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb is not installed") from exc
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection("memory_vectors")
        self._dim = dim

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        if not ids:
            return
        self._collection.add(ids=ids, embeddings=vectors)

    def search(self, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        if top_k <= 0:
            return []
        results = self._collection.query(query_embeddings=[vector], n_results=top_k)
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        scored = []
        for idx, distance in zip(ids, distances):
            score = 1.0 / (1.0 + float(distance))
            scored.append((idx, score))
        return scored
