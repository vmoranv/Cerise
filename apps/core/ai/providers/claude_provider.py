"""
Claude Provider

Provider implementation for Anthropic Claude API.
"""

from collections.abc import AsyncIterator

from .base import (
    BaseProvider,
    ChatOptions,
    ChatResponse,
    Message,
    ProviderCapabilities,
)


class ClaudeProvider(BaseProvider):
    """Anthropic Claude API provider"""

    name = "claude"
    DEFAULT_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",
    ]

    def __init__(self, api_key: str, models: list[str] | None = None):
        self.api_key = api_key
        self._available_models = models or self.DEFAULT_MODELS
        self._client = None

    @property
    def available_models(self) -> list[str]:
        return self._available_models

    @property
    def client(self):
        """Lazy load Anthropic client"""
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        # Separate system message
        system_msg = next(
            (m.content for m in messages if m.role == "system"),
            None,
        )
        chat_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        response = await self.client.messages.create(
            model=options.model,
            max_tokens=options.max_tokens,
            system=system_msg or "",
            messages=chat_messages,
        )

        return ChatResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason or "stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Streaming chat completion"""
        system_msg = next(
            (m.content for m in messages if m.role == "system"),
            None,
        )
        chat_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        async with self.client.messages.stream(
            model=options.model,
            max_tokens=options.max_tokens,
            system=system_msg or "",
            messages=chat_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities"""
        return ProviderCapabilities(
            streaming=True,
            function_calling=True,
            vision=True,
            max_context_length=200000,
        )
