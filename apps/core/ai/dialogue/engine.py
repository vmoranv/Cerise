"""
Dialogue Engine

Core engine for managing AI conversations with multi-provider support.
"""

import logging
from typing import TYPE_CHECKING

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
from ..providers import Message as ProviderMessage
from .context import build_context_messages
from .ports import AbilityRegistryProtocol, ProviderRegistryProtocol
from .session import Session
from .streaming import StreamChatMixin
from .tools import handle_tool_calls

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..skills import SkillService


class DialogueEngine(StreamChatMixin):
    """Main dialogue engine for AI conversations"""

    def __init__(
        self,
        message_bus: EventBus,
        default_provider: str = "openai",
        default_model: str = "gpt-4o",
        default_temperature: float = 0.7,
        default_top_p: float = 1.0,
        default_max_tokens: int = 2048,
        system_prompt: str = "",
        memory_service: MemoryService | None = None,
        memory_recall: bool = True,
        skill_service: "SkillService | None" = None,
        skill_recall: bool = False,
        skill_top_k: int = 3,
        provider_registry: ProviderRegistryProtocol | None = None,
        ability_registry: AbilityRegistryProtocol | None = None,
    ):
        self.default_provider = default_provider
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        self.default_system_prompt = system_prompt
        self._sessions: dict[str, Session] = {}
        self._message_bus = message_bus
        self._memory_service = memory_service
        self._memory_recall = memory_recall
        self._skill_service = skill_service
        self._skill_recall = skill_recall
        self._skill_top_k = max(1, int(skill_top_k))
        self._provider_registry = provider_registry or ProviderRegistry
        self._ability_registry = ability_registry or AbilityRegistry

    @staticmethod
    def _content_to_text(content: str | list[dict]) -> str:
        if isinstance(content, str):
            return content
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
            elif item.get("type") == "image_url":
                parts.append("[image]")
            else:
                parts.append("[content]")
        return "\n".join(parts).strip()

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
        user_message: str | list[dict],
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        use_tools: bool = True,
    ) -> str:
        """Send a message and get a response"""
        user_text = self._content_to_text(user_message)
        # Add user message
        session.add_user_message(user_message)

        # Emit event
        await self._message_bus.emit(
            DIALOGUE_USER_MESSAGE,
            build_dialogue_user_message(session_id=session.id, content=user_text),
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
            query=user_text,
            memory_service=self._memory_service,
            memory_recall=self._memory_recall,
        )

        if self._skill_service and self._skill_recall:
            try:
                skills = await self._skill_service.search(user_text, top_k=self._skill_top_k)
                injection = self._skill_service.build_injection_block(skills)
            except Exception:
                injection = ""
            if injection:
                insert_at = 1 if messages and messages[0].role == "system" else 0
                messages.insert(insert_at, ProviderMessage(role="system", content=injection))

        temperature = self.default_temperature if temperature is None else temperature
        top_p = self.default_top_p if top_p is None else top_p
        max_tokens = self.default_max_tokens if max_tokens is None else max_tokens

        # Prepare options
        options = ChatOptions(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
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
                skill_service=self._skill_service,
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

    async def proactive_chat(
        self,
        session: Session,
        *,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_tools: bool = False,
    ) -> str:
        """Generate a proactive assistant message without adding a user message."""
        if use_tools:
            logger.warning("Proactive chat does not support tool calls; skipping tools.")

        provider_name = provider or self.default_provider
        ai_provider = self._provider_registry.get(provider_name)
        if not ai_provider:
            raise ValueError(f"Provider not found: {provider_name}")

        messages = await build_context_messages(
            session=session,
            query=prompt,
            memory_service=self._memory_service,
            memory_recall=self._memory_recall,
        )
        messages.append(ProviderMessage(role="user", content=prompt))

        options = ChatOptions(
            model=model or self.default_model,
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=max_tokens or 1024,
        )

        response = await ai_provider.chat(messages, options)
        response_content = response.content
        session.add_assistant_message(response_content)

        await self._message_bus.emit(
            DIALOGUE_ASSISTANT_RESPONSE,
            build_dialogue_assistant_response(
                session_id=session.id,
                content=response_content,
                model=response.model,
            ),
            source="proactive_chat",
        )

        return response_content

    def set_system_prompt(self, session: Session, prompt: str) -> None:
        """Update the system prompt for a session"""
        session.system_prompt = prompt

    def get_all_sessions(self) -> list[Session]:
        """Get all active sessions"""
        return list(self._sessions.values())
