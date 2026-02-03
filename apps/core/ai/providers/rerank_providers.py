"""
Rerank providers.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import AsyncIterator

from .base import BaseProvider, ChatOptions, ChatResponse, Message, ProviderCapabilities
from .rerank_http_provider import RerankHttpProvider


class VllmRerankProvider(RerankHttpProvider):
    """vLLM rerank provider (/v1/rerank)."""

    name = "vllm_rerank"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        headers: dict | None = None,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model or "BAAI/bge-reranker-base",
            timeout=timeout,
            headers=headers,
        )


class XinferenceRerankProvider(RerankHttpProvider):
    """Xinference rerank provider (assumes /v1/rerank compatible endpoint)."""

    name = "xinference_rerank"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9997",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        headers: dict | None = None,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model or "BAAI/bge-reranker-base",
            timeout=timeout,
            headers=headers,
        )


class BailianRerankProvider(BaseProvider):
    """Bailian (DashScope) rerank provider."""

    name = "bailian_rerank"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        return_documents: bool = False,
        instruct: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url or "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
        self.model = model or "qwen3-rerank"
        self.timeout = timeout
        self.return_documents = return_documents
        self.instruct = instruct or ""

    @property
    def available_models(self) -> list[str]:
        return [self.model]

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
        payload = self._build_payload(query, documents, top_k, model or self.model)
        response = await self._post_json(payload)
        return self._parse_results(response)

    def _build_payload(self, query: str, documents: list[str], top_k: int | None, model: str) -> dict:
        base = {"model": model, "input": {"query": query, "documents": documents}}
        params: dict = {}
        if top_k is not None:
            params["top_n"] = top_k
        if self.return_documents:
            params["return_documents"] = True
        if self.instruct and model == "qwen3-rerank":
            params["instruct"] = self.instruct
        if params:
            base["parameters"] = params
        return base

    async def _post_json(self, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)

    def _parse_results(self, data: dict) -> list[tuple[int, float]]:
        if data.get("code", "200") != "200":
            return []
        results = data.get("output", {}).get("results", [])
        reranked: list[tuple[int, float]] = []
        for idx, item in enumerate(results):
            index = item.get("index", idx)
            score = item.get("relevance_score", 0.0)
            reranked.append((int(index), float(score)))
        return reranked
