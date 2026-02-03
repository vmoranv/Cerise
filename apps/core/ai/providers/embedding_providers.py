"""
Embedding providers.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator

from .base import BaseProvider, ChatOptions, ChatResponse, Message, ProviderCapabilities


class OpenAIEmbeddingProvider(BaseProvider):
    """OpenAI embedding provider (embedding-only)."""

    name = "openai_embedding"

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        model: str | None = None,
        custom_headers: dict | None = None,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        retry_jitter: float = 0.1,
    ):
        keys: list[str] = []
        if isinstance(api_keys, list):
            keys.extend([item for item in api_keys if isinstance(item, str) and item.strip()])
        if isinstance(api_key, str) and api_key.strip():
            keys.insert(0, api_key)
        if not keys:
            raise ValueError("OpenAI embedding provider requires api_key or api_keys")

        self._api_keys = keys
        self._key_index = 0
        self._rng = random.Random()
        self._lock = asyncio.Lock()
        self._clients: dict[str, object] = {}

        self.base_url = base_url
        self.model = model or "text-embedding-3-small"
        self.custom_headers = custom_headers or {}
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self.retry_jitter = max(0.0, float(retry_jitter))

    @property
    def available_models(self) -> list[str]:
        return [self.model]

    def _get_current_key(self) -> str:
        return self._api_keys[self._key_index]

    def _rotate_key(self) -> None:
        if len(self._api_keys) <= 1:
            return
        self._key_index = (self._key_index + 1) % len(self._api_keys)

    def _get_client(self, api_key: str):
        client = self._clients.get(api_key)
        if client is not None:
            return client
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url,
            default_headers=self.custom_headers or None,
        )
        self._clients[api_key] = client
        return client

    def _classify_error(self, exc: Exception) -> tuple[bool, bool]:
        try:
            from openai import (
                APIConnectionError,
                APITimeoutError,
                AuthenticationError,
                InternalServerError,
                RateLimitError,
            )
        except Exception:
            return False, False

        if isinstance(exc, (APITimeoutError, APIConnectionError, InternalServerError)):
            return True, False
        if isinstance(exc, (RateLimitError, AuthenticationError)):
            return True, True
        return False, False

    async def _sleep_backoff(self, attempt: int) -> None:
        if self.retry_backoff <= 0:
            return
        base = self.retry_backoff * (2**attempt)
        jitter = self._rng.random() * self.retry_jitter if self.retry_jitter else 0.0
        await asyncio.sleep(base + jitter)

    async def _call_with_retry(self, fn):
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            async with self._lock:
                api_key = self._get_current_key()
                client = self._get_client(api_key)

            try:
                return await fn(client)
            except Exception as exc:
                last_exc = exc
                retryable, rotate = self._classify_error(exc)
                if not retryable or attempt >= self.max_retries:
                    raise
                if rotate:
                    async with self._lock:
                        self._rotate_key()
                await self._sleep_backoff(attempt)
        assert last_exc is not None
        raise last_exc

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
        async def _do_request(client):
            return await client.embeddings.create(
                model=model or self.model,
                input=texts,
            )

        response = await self._call_with_retry(_do_request)
        return [item.embedding for item in response.data]


class GeminiEmbeddingProvider(BaseProvider):
    """Gemini embedding provider (embedding-only)."""

    name = "gemini_embedding"

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        model: str | None = None,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        retry_jitter: float = 0.1,
    ):
        keys: list[str] = []
        if isinstance(api_keys, list):
            keys.extend([item for item in api_keys if isinstance(item, str) and item.strip()])
        if isinstance(api_key, str) and api_key.strip():
            keys.insert(0, api_key)
        if not keys:
            raise ValueError("Gemini embedding provider requires api_key or api_keys")

        self._api_keys = keys
        self._key_index = 0
        self._rng = random.Random()
        self._lock = asyncio.Lock()

        self.model = model or "gemini-embedding-exp-03-07"
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self.retry_jitter = max(0.0, float(retry_jitter))
        self._client = None

    @property
    def available_models(self) -> list[str]:
        return [self.model]

    @property
    def client(self):
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self._api_keys[self._key_index])
            self._client = genai
        return self._client

    def _rotate_key(self) -> None:
        if len(self._api_keys) <= 1:
            return
        self._key_index = (self._key_index + 1) % len(self._api_keys)
        if self._client is not None:
            self._client.configure(api_key=self._api_keys[self._key_index])

    def _classify_error(self, exc: Exception) -> tuple[bool, bool]:
        message = str(exc)
        if "429" in message or "rate limit" in message.lower():
            return True, True
        if "API key not valid" in message or "invalid" in message.lower() and "key" in message.lower():
            return True, True
        return True, False

    async def _sleep_backoff(self, attempt: int) -> None:
        if self.retry_backoff <= 0:
            return
        base = self.retry_backoff * (2**attempt)
        jitter = self._rng.random() * self.retry_jitter if self.retry_jitter else 0.0
        await asyncio.sleep(base + jitter)

    async def _call_with_retry(self, fn):
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with self._lock:
                    return await fn()
            except Exception as exc:
                last_exc = exc
                retryable, rotate = self._classify_error(exc)
                if not retryable or attempt >= self.max_retries:
                    raise
                if rotate:
                    async with self._lock:
                        self._rotate_key()
                await self._sleep_backoff(attempt)
        assert last_exc is not None
        raise last_exc

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

        async def _do_request():
            if len(texts) == 1:
                result = await asyncio.to_thread(
                    self.client.embed_content,
                    model=model_name,
                    content=texts[0],
                )
                embedding = (
                    getattr(result, "embedding", None) if hasattr(result, "embedding") else result.get("embedding")
                )
                return [embedding]

            result = await asyncio.to_thread(
                self.client.embed_content,
                model=model_name,
                content=texts,
            )
            embeddings = (
                getattr(result, "embeddings", None) if hasattr(result, "embeddings") else result.get("embeddings")
            )
            if not embeddings:
                return []
            return [item.get("values", item) for item in embeddings]

        return await self._call_with_retry(_do_request)
