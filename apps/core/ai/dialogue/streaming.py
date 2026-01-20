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
    _provider_registry: ProviderRegistryProtocol
    _memory_service: MemoryService | None
    _memory_recall: bool

    async def stream_chat(
        self,
        session: Session,
        user_message: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Send a message and stream the response."""
        session.add_user_message(user_message)

        provider_name = provider or self.default_provider
        ai_provider = self._provider_registry.get(provider_name)
        if not ai_provider:
            raise ValueError(f"Provider not found: {provider_name}")

        messages = await build_context_messages(
            session=session,
            query=user_message,
            memory_service=self._memory_service,
            memory_recall=self._memory_recall,
        )

        options = ChatOptions(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        full_response = ""
        async for chunk in ai_provider.stream_chat(messages, options):
            full_response += chunk
            yield chunk

        session.add_assistant_message(full_response)
