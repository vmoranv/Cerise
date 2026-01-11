"""
Gemini Provider

Provider implementation for Google Gemini API.
"""

from collections.abc import AsyncIterator

from .base import (
    BaseProvider,
    ChatOptions,
    ChatResponse,
    Message,
    ProviderCapabilities,
)


class GeminiProvider(BaseProvider):
    """Google Gemini API provider"""

    name = "gemini"
    available_models = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        """Lazy load Gemini client"""
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai
        return self._client

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        model = self.client.GenerativeModel(options.model)

        # Convert messages to Gemini format
        history = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        # Start chat with system instruction if provided
        model = self.client.GenerativeModel(
            options.model,
            system_instruction=system_instruction,
        )
        chat = model.start_chat(history=history[:-1] if history else [])

        # Get last user message
        last_msg = history[-1]["parts"][0] if history else ""

        response = await chat.send_message_async(
            last_msg,
            generation_config={
                "temperature": options.temperature,
                "max_output_tokens": options.max_tokens,
                "top_p": options.top_p,
            },
        )

        return ChatResponse(
            content=response.text,
            model=options.model,
            usage={},  # Gemini doesn't provide token counts easily
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Streaming chat completion"""
        model = self.client.GenerativeModel(options.model)

        history = []
        for msg in messages:
            if msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        chat = model.start_chat(history=history[:-1] if history else [])
        last_msg = history[-1]["parts"][0] if history else ""

        response = await chat.send_message_async(
            last_msg,
            generation_config={
                "temperature": options.temperature,
                "max_output_tokens": options.max_tokens,
            },
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities"""
        return ProviderCapabilities(
            streaming=True,
            function_calling=True,
            vision=True,
            max_context_length=1000000,  # Gemini 1.5 supports 1M tokens
        )
