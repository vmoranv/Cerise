"""Dialogue tool-call handling helpers."""

from __future__ import annotations

import logging

from ...abilities import AbilityContext
from ..providers import ChatOptions
from ..providers import Message as ProviderMessage
from .ports import AbilityRegistryProtocol, ProviderRegistryProtocol
from .session import Session

logger = logging.getLogger(__name__)


def _build_tool_context(session: Session) -> AbilityContext:
    return AbilityContext(
        user_id=session.user_id,
        session_id=session.id,
        permissions=["system.execute", "network.http"],
    )


async def handle_tool_calls(
    *,
    session: Session,
    response,
    provider_name: str,
    options: ChatOptions,
    ability_registry: AbilityRegistryProtocol,
    provider_registry: ProviderRegistryProtocol,
) -> str:
    """Process tool calls from assistant."""
    for tool_call in response.tool_calls:
        tool_name = tool_call.get("function", {}).get("name", "")
        tool_args = tool_call.get("function", {}).get("arguments", {})
        tool_id = tool_call.get("id", "")

        logger.info("Executing tool: %s", tool_name)

        context = _build_tool_context(session)
        result = await ability_registry.execute(tool_name, tool_args, context)

        session.add_tool_result(
            tool_id,
            str(result.data) if result.success else result.error or "Error",
            name=tool_name,
        )

    ai_provider = provider_registry.get(provider_name)
    messages = [ProviderMessage(role=m["role"], content=m["content"]) for m in session.get_context_messages()]

    final_response = await ai_provider.chat(messages, options)
    return final_response.content
