"""
Embedding providers adapted from AstrBot.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from .base import BaseProvider, ChatOptions, ChatResponse, Message, ProviderCapabilities


class OpenAIEmbeddingProvider(BaseProvider):
    """OpenAI embedding provider (embedding-only)."""

    name = "openai_embedding"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        custom_headers: dict | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model or "text-embedding-3-small"
        self.custom_headers = custom_headers or {}
        self._client = None

    @property
    def available_models(self) -> list[str]:
        return [self.model]

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers=self.custom_headers or None,
            )
        return self._client

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:
        raise NotImplementedError("Embedding provider does not support chat")

    async def stream_chat(self, messages: list[Message], options: ChatOptions) -> AsyncIterator[str]:
        raise NotImplementedError("Embedding provider does not support streaming")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=False,
            streaming=False,
            function_calling=False,
            vision=False,
            embeddings=True,
            rerank=False,
            max_context_length=0,
        )

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=model or self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]


class GeminiEmbeddingProvider(BaseProvider):
    """Gemini embedding provider (embedding-only)."""

    name = "gemini_embedding"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ):
        self.api_key = api_key
        self.model = model or "gemini-embedding-exp-03-07"
        self._client = None

    @property
    def available_models(self) -> list[str]:
        return [self.model]

    @property
    def client(self):
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai
        return self._client

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:
        raise NotImplementedError("Embedding provider does not support chat")

    async def stream_chat(self, messages: list[Message], options: ChatOptions) -> AsyncIterator[str]:
        raise NotImplementedError("Embedding provider does not support streaming")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=False,
            streaming=False,
            function_calling=False,
            vision=False,
            embeddings=True,
            rerank=False,
            max_context_length=0,
        )

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model_name = model or self.model
        if len(texts) == 1:
            result = await asyncio.to_thread(
                self.client.embed_content,
                model=model_name,
                content=texts[0],
            )
            embedding = getattr(result, "embedding", None) if hasattr(result, "embedding") else result.get("embedding")
            return [embedding]
        result = await asyncio.to_thread(
            self.client.embed_content,
            model=model_name,
            content=texts,
        )
        embeddings = getattr(result, "embeddings", None) if hasattr(result, "embeddings") else result.get("embeddings")
        if not embeddings:
            return []
        return [item.get("values", item) for item in embeddings]
