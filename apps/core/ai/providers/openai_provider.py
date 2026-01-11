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
    available_models = [
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
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.organization = organization
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                organization=self.organization,
            )
        return self._client

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        response = await self.client.chat.completions.create(
            model=options.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            top_p=options.top_p,
            stop=options.stop,
            tools=options.tools,
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
        stream = await self.client.chat.completions.create(
            model=options.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            top_p=options.top_p,
            stream=True,
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
            max_context_length=128000,
        )
