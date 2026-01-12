"""
HTTP Rerank Provider

Generic rerank adapter for /v1/rerank style APIs.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from collections.abc import AsyncIterator

from .base import BaseProvider, ChatOptions, ChatResponse, Message, ProviderCapabilities


class RerankHttpProvider(BaseProvider):
    """Generic rerank provider for HTTP endpoints."""

    name = "rerank_http"

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        headers: dict | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model or ""
        self.timeout = timeout
        self.headers = headers or {}

    @property
    def available_models(self) -> list[str]:
        return [self.model] if self.model else []

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:
        raise NotImplementedError("Rerank provider does not support chat")

    async def stream_chat(self, messages: list[Message], options: ChatOptions) -> AsyncIterator[str]:
        raise NotImplementedError("Rerank provider does not support streaming")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=False,
            streaming=False,
            function_calling=False,
            vision=False,
            embeddings=False,
            rerank=True,
            max_context_length=0,
        )

    async def rerank(
        self,
        query: str,
        documents: list[str],
        model: str | None = None,
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        if not documents:
            return []
        payload = {
            "query": query,
            "documents": documents,
        }
        if model or self.model:
            payload["model"] = model or self.model
        if top_k:
            payload["top_n"] = top_k

        response_data = await asyncio.to_thread(self._post_json, payload)
        results = response_data.get("results") or response_data.get("data") or []
        reranked: list[tuple[int, float]] = []
        for item in results:
            index = item.get("index")
            score = item.get("score") or item.get("relevance") or item.get("relevance_score")
            if index is None or score is None:
                continue
            reranked.append((int(index), float(score)))
        return reranked

    def _post_json(self, payload: dict) -> dict:
        url = self.base_url
        if not url.endswith("/v1/rerank"):
            url = f"{url}/v1/rerank"
        headers = {"Content-Type": "application/json"}
        headers.update(self.headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)
