"""
Dialogue Engine

Core engine for managing AI conversations with multi-provider support.
"""

import logging

from ...abilities import AbilityRegistry
from ...contracts.events import (
    DIALOGUE_ASSISTANT_RESPONSE,
    DIALOGUE_USER_MESSAGE,
    build_dialogue_assistant_response,
    build_dialogue_user_message,
)
from ...infrastructure import EventBus
from ...services.ports import MemoryService
from ..providers import ChatOptions, ProviderRegistry
from .context import build_context_messages
from .ports import AbilityRegistryProtocol, ProviderRegistryProtocol
from .session import Session
from .streaming import StreamChatMixin
from .tools import handle_tool_calls

logger = logging.getLogger(__name__)


class DialogueEngine(StreamChatMixin):
    """Main dialogue engine for AI conversations"""

    def __init__(
        self,
        message_bus: EventBus,
        default_provider: str = "openai",
        default_model: str = "gpt-4o",
        system_prompt: str = "",
        memory_service: MemoryService | None = None,
        memory_recall: bool = True,
        provider_registry: ProviderRegistryProtocol | None = None,
        ability_registry: AbilityRegistryProtocol | None = None,
    ):
        self.default_provider = default_provider
        self.default_model = default_model
        self.default_system_prompt = system_prompt
        self._sessions: dict[str, Session] = {}
        self._message_bus = message_bus
        self._memory_service = memory_service
        self._memory_recall = memory_recall
        self._provider_registry = provider_registry or ProviderRegistry
        self._ability_registry = ability_registry or AbilityRegistry

    def create_session(
        self,
        user_id: str = "",
        system_prompt: str | None = None,
        session_id: str | None = None,
    ) -> Session:
        """Create a new conversation session"""
        session = Session(
            user_id=user_id,
            system_prompt=system_prompt or self.default_system_prompt,
        )
        if session_id:
            session.id = session_id
        self._sessions[session.id] = session
        logger.info(f"Created session: {session.id}")
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get an existing session"""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def chat(
        self,
        session: Session,
        user_message: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_tools: bool = True,
    ) -> str:
        """Send a message and get a response"""
        # Add user message
        session.add_user_message(user_message)

        # Emit event
        await self._message_bus.emit(
            DIALOGUE_USER_MESSAGE,
            build_dialogue_user_message(session_id=session.id, content=user_message),
            source="dialogue_engine",
        )

        # Get provider
        provider_name = provider or self.default_provider
        ai_provider = self._provider_registry.get(provider_name)
        if not ai_provider:
            raise ValueError(f"Provider not found: {provider_name}")

        # Prepare messages
        messages = await build_context_messages(
            session=session,
            query=user_message,
            memory_service=self._memory_service,
            memory_recall=self._memory_recall,
        )

        # Prepare options
        options = ChatOptions(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=self._ability_registry.get_tool_schemas() if use_tools else None,
        )

        # Call AI
        response = await ai_provider.chat(messages, options)

        # Handle tool calls
        if response.tool_calls and use_tools:
            response_content = await handle_tool_calls(
                session=session,
                response=response,
                provider_name=provider_name,
                options=options,
                ability_registry=self._ability_registry,
                provider_registry=self._provider_registry,
            )
        else:
            response_content = response.content

        # Add assistant message
        session.add_assistant_message(response_content)

        # Emit response event
        await self._message_bus.emit(
            DIALOGUE_ASSISTANT_RESPONSE,
            build_dialogue_assistant_response(
                session_id=session.id,
                content=response_content,
                model=response.model,
            ),
            source="dialogue_engine",
        )

        return response_content

    def set_system_prompt(self, session: Session, prompt: str) -> None:
        """Update the system prompt for a session"""
        session.system_prompt = prompt

    def get_all_sessions(self) -> list[Session]:
        """Get all active sessions"""
        return list(self._sessions.values())
