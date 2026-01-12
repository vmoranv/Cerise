"""
Dialogue Engine

Core engine for managing AI conversations with multi-provider support.
"""

import logging
from collections.abc import AsyncIterator
from typing import Protocol

from ...abilities import AbilityContext, AbilityRegistry
from ...infrastructure import MessageBus
from ..memory import MemoryEngine
from ..providers import BaseProvider, ChatOptions, ProviderRegistry
from ..providers import Message as ProviderMessage
from .session import Session

logger = logging.getLogger(__name__)


class ProviderRegistryProtocol(Protocol):
    """Minimal provider registry interface."""

    def get(self, provider_id: str) -> BaseProvider | None:
        """Get a provider instance by id."""


class AbilityRegistryProtocol(Protocol):
    """Minimal ability registry interface."""

    def get_tool_schemas(self) -> list[dict]:
        """Return tool schemas for the provider."""

    async def execute(self, ability_name: str, params: dict, context: AbilityContext):
        """Execute an ability by name."""


class DialogueEngine:
    """Main dialogue engine for AI conversations"""

    def __init__(
        self,
        default_provider: str = "openai",
        default_model: str = "gpt-4o",
        system_prompt: str = "",
        message_bus: MessageBus | None = None,
        memory_engine: MemoryEngine | None = None,
        memory_recall: bool = True,
        provider_registry: ProviderRegistryProtocol | None = None,
        ability_registry: AbilityRegistryProtocol | None = None,
    ):
        self.default_provider = default_provider
        self.default_model = default_model
        self.default_system_prompt = system_prompt
        self._sessions: dict[str, Session] = {}
        self._message_bus = message_bus or MessageBus()
        self._memory_engine = memory_engine
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
            "dialogue.user_message",
            {"session_id": session.id, "content": user_message},
            source="dialogue_engine",
        )

        # Get provider
        provider_name = provider or self.default_provider
        ai_provider = self._provider_registry.get(provider_name)
        if not ai_provider:
            raise ValueError(f"Provider not found: {provider_name}")

        # Prepare messages
        messages = await self._build_context_messages(session, user_message)

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
            response_content = await self._handle_tool_calls(session, response, provider_name, options)
        else:
            response_content = response.content

        # Add assistant message
        session.add_assistant_message(response_content)

        # Emit response event
        await self._message_bus.emit(
            "dialogue.assistant_response",
            {
                "session_id": session.id,
                "content": response_content,
                "model": response.model,
            },
            source="dialogue_engine",
        )

        return response_content

    async def stream_chat(
        self,
        session: Session,
        user_message: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Send a message and stream the response"""
        # Add user message
        session.add_user_message(user_message)

        # Get provider
        provider_name = provider or self.default_provider
        ai_provider = self._provider_registry.get(provider_name)
        if not ai_provider:
            raise ValueError(f"Provider not found: {provider_name}")

        # Prepare messages
        messages = await self._build_context_messages(session, user_message)

        options = ChatOptions(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        # Stream response
        full_response = ""
        async for chunk in ai_provider.stream_chat(messages, options):
            full_response += chunk
            yield chunk

        # Add complete response
        session.add_assistant_message(full_response)

    async def _handle_tool_calls(
        self,
        session: Session,
        response,
        provider_name: str,
        options: ChatOptions,
    ) -> str:
        """Process tool calls from assistant"""
        results = []

        for tool_call in response.tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_args = tool_call.get("function", {}).get("arguments", {})
            tool_id = tool_call.get("id", "")

            logger.info(f"Executing tool: {tool_name}")

            # Execute ability
            context = AbilityContext(
                user_id=session.user_id,
                session_id=session.id,
                permissions=["system.execute", "network.http"],  # Default permissions
            )

            result = await self._ability_registry.execute(tool_name, tool_args, context)

            # Add tool result to session
            session.add_tool_result(
                tool_id,
                str(result.data) if result.success else result.error or "Error",
                name=tool_name,
            )

            results.append(result)

        # Get follow-up response from AI
        ai_provider = self._provider_registry.get(provider_name)
        messages = [ProviderMessage(role=m["role"], content=m["content"]) for m in session.get_context_messages()]

        final_response = await ai_provider.chat(messages, options)
        return final_response.content

    def set_system_prompt(self, session: Session, prompt: str) -> None:
        """Update the system prompt for a session"""
        session.system_prompt = prompt

    def get_all_sessions(self) -> list[Session]:
        """Get all active sessions"""
        return list(self._sessions.values())

    async def _build_context_messages(self, session: Session, query: str) -> list[ProviderMessage]:
        context = session.get_context_messages()
        memory_context = ""
        if self._memory_engine and self._memory_recall:
            try:
                results = await self._memory_engine.recall(
                    query,
                    limit=self._memory_engine.config.recall.top_k if self._memory_engine.config else 5,
                    session_id=session.id,
                )
                memory_context = self._memory_engine.format_context(results)
            except Exception:  # pragma: no cover - recall is optional
                logger.exception("Memory recall failed")
        if memory_context:
            memory_message = {"role": "system", "content": memory_context}
            if context and context[0].get("role") == "system":
                context = [context[0], memory_message] + context[1:]
            else:
                context = [memory_message] + context
        return [ProviderMessage(role=m["role"], content=m["content"]) for m in context]
