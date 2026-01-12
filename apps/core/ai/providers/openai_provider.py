"""
OpenAI Provider

Provider implementation for OpenAI API (GPT-4, GPT-4o, etc.)
"""

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
        api_key: str,
        base_url: str | None = None,
        organization: str | None = None,
        models: list[str] | None = None,
        embedding_model: str | None = None,
        custom_headers: dict | None = None,
        extra_body: dict | None = None,
        api_version: str | None = None,
        azure_endpoint: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.organization = organization
        self._available_models = models or self.DEFAULT_MODELS
        self._client = None
        self.embedding_model = embedding_model or "text-embedding-3-small"
        self.custom_headers = custom_headers or {}
        self.extra_body = extra_body or {}
        self.api_version = api_version
        self.azure_endpoint = azure_endpoint
        self.timeout = timeout

    @property
    def available_models(self) -> list[str]:
        return self._available_models

    @property
    def client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            if self.api_version or self.azure_endpoint:
                from openai import AsyncAzureOpenAI

                self._client = AsyncAzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint or self.base_url,
                    default_headers=self.custom_headers or None,
                    timeout=self.timeout,
                )
            else:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    organization=self.organization,
                    default_headers=self.custom_headers or None,
                    timeout=self.timeout,
                )
        return self._client

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        extra_body = self._build_extra_body()
        response = await self.client.chat.completions.create(
            model=options.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            top_p=options.top_p,
            stop=options.stop,
            tools=options.tools,
            extra_body=extra_body if extra_body else None,
        )

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
        stream = await self.client.chat.completions.create(
            model=options.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            top_p=options.top_p,
            stream=True,
            extra_body=extra_body if extra_body else None,
        )

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
        response = await self.client.embeddings.create(
            model=model or self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _build_extra_body(self) -> dict:
        return dict(self.extra_body) if self.extra_body else {}
