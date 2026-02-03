"""
Dialogue streaming helpers.
"""

from collections.abc import AsyncIterator

from ...services.ports import MemoryService
from ..providers import ChatOptions
from .context import build_context_messages
from .ports import ProviderRegistryProtocol
from .session import Session


class StreamChatMixin:
    default_provider: str
    default_model: str
    default_temperature: float
    default_top_p: float
    default_max_tokens: int
    _provider_registry: ProviderRegistryProtocol
    _memory_service: MemoryService | None
    _memory_recall: bool

    async def stream_chat(
        self,
        session: Session,
        user_message: str | list[dict],
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and stream the response."""
        user_text = self._content_to_text(user_message)
        session.add_user_message(user_message)

        provider_name = provider or self.default_provider
        ai_provider = self._provider_registry.get(provider_name)
        if not ai_provider:
            raise ValueError(f"Provider not found: {provider_name}")

        messages = await build_context_messages(
            session=session,
            query=user_text,
            memory_service=self._memory_service,
            memory_recall=self._memory_recall,
        )

        temperature = self.default_temperature if temperature is None else temperature
        top_p = self.default_top_p if top_p is None else top_p
        max_tokens = self.default_max_tokens if max_tokens is None else max_tokens

        options = ChatOptions(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            stream=True,
        )

        full_response = ""
        async for chunk in ai_provider.stream_chat(messages, options):
            full_response += chunk
            yield chunk

        session.add_assistant_message(full_response)
