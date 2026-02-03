"""
OpenAI Provider

Provider implementation for OpenAI API (GPT-4, GPT-4o, etc.)
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator

from .base import (
    BaseProvider,
    ChatOptions,
    ChatResponse,
    Message,
    ProviderCapabilities,
)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""

    name = "openai"
    DEFAULT_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        organization: str | None = None,
        models: list[str] | None = None,
        embedding_model: str | None = None,
        custom_headers: dict | None = None,
        extra_body: dict | None = None,
        api_version: str | None = None,
        azure_endpoint: str | None = None,
        timeout: float | None = None,
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
            raise ValueError("OpenAI provider requires api_key or api_keys")

        self._api_keys = keys
        self._key_index = 0
        self._rng = random.Random()
        self._lock = asyncio.Lock()
        self._clients: dict[str, object] = {}

        self.base_url = base_url
        self.organization = organization
        self._available_models = models or self.DEFAULT_MODELS
        self.embedding_model = embedding_model or "text-embedding-3-small"
        self.custom_headers = custom_headers or {}
        self.extra_body = extra_body or {}
        self.api_version = api_version
        self.azure_endpoint = azure_endpoint
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self.retry_jitter = max(0.0, float(retry_jitter))

    @property
    def available_models(self) -> list[str]:
        return self._available_models

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

        if self.api_version or self.azure_endpoint:
            from openai import AsyncAzureOpenAI

            client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint or self.base_url,
                default_headers=self.custom_headers or None,
                timeout=self.timeout,
            )
        else:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=api_key,
                base_url=self.base_url,
                organization=self.organization,
                default_headers=self.custom_headers or None,
                timeout=self.timeout,
            )

        self._clients[api_key] = client
        return client

    def _classify_error(self, exc: Exception) -> tuple[bool, bool]:
        """Return (retryable, rotate_key)."""
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

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        extra_body = self._build_extra_body()

        async def _do_request(client):
            return await client.chat.completions.create(
                model=options.model,
                messages=[self._to_openai_message(m) for m in messages],
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                top_p=options.top_p,
                stop=options.stop,
                tools=options.tools,
                extra_body=extra_body if extra_body else None,
            )

        response = await self._call_with_retry(_do_request)

        choice = response.choices[0]
        return ChatResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            tool_calls=[tc.model_dump() for tc in choice.message.tool_calls] if choice.message.tool_calls else None,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Streaming chat completion"""
        extra_body = self._build_extra_body()

        async def _do_request(client):
            return await client.chat.completions.create(
                model=options.model,
                messages=[self._to_openai_message(m) for m in messages],
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                top_p=options.top_p,
                stream=True,
                extra_body=extra_body if extra_body else None,
            )

        stream = await self._call_with_retry(_do_request)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities"""
        return ProviderCapabilities(
            streaming=True,
            function_calling=True,
            vision=True,
            embeddings=True,
            max_context_length=128000,
        )

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Create embeddings for texts."""

        async def _do_request(client):
            return await client.embeddings.create(
                model=model or self.embedding_model,
                input=texts,
            )

        response = await self._call_with_retry(_do_request)
        return [item.embedding for item in response.data]

    def _build_extra_body(self) -> dict:
        return dict(self.extra_body) if self.extra_body else {}

    @staticmethod
    def _to_openai_message(message: Message) -> dict:
        payload: dict = {"role": message.role, "content": message.content}
        if message.name:
            payload["name"] = message.name
        if message.tool_calls:
            payload["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        return payload
