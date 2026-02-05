"""Dialogue tool-call handling helpers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ...abilities import AbilityContext
from ...config import get_config_loader
from ..providers import ChatOptions
from ..providers import Message as ProviderMessage
from .ports import AbilityRegistryProtocol, ProviderRegistryProtocol
from .session import Session

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..skills import SkillService


def _build_tool_context(session: Session) -> AbilityContext:
    loader = get_config_loader()
    config = loader.get_app_config()
    permissions = list(config.tools.permissions)
    return AbilityContext(
        user_id=session.user_id,
        session_id=session.id,
        permissions=permissions,
    )


def _truncate(text: str, *, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n...[truncated]"


def _format_tool_result(payload, *, max_chars: int) -> str:
    if payload is None:
        return ""
    if isinstance(payload, (dict, list)):
        try:
            text = json.dumps(payload, ensure_ascii=False)
        except Exception:
            text = str(payload)
    else:
        text = str(payload)
    return _truncate(text, max_chars=max_chars)


async def handle_tool_calls(
    *,
    session: Session,
    response,
    provider_name: str,
    options: ChatOptions,
    ability_registry: AbilityRegistryProtocol,
    provider_registry: ProviderRegistryProtocol,
    skill_service: SkillService | None = None,
    max_rounds: int = 3,
) -> str:
    """Process tool calls from assistant."""
    ai_provider = provider_registry.get(provider_name)
    if not ai_provider:
        raise ValueError(f"Provider not found: {provider_name}")

    current = response
    rounds = 0
    max_rounds = max(1, int(max_rounds))
    max_chars = max(0, int(get_config_loader().get_app_config().tools.max_result_chars))

    while current.tool_calls and rounds < max_rounds:
        rounds += 1
        session.add_assistant_message(current.content or "", tool_calls=current.tool_calls)

        for tool_call in current.tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_args = tool_call.get("function", {}).get("arguments", {})
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    tool_args = {}
            if tool_args is None or not isinstance(tool_args, dict):
                tool_args = {}
            tool_id = tool_call.get("id", "") or None

            logger.info("Executing tool: %s", tool_name)

            context = _build_tool_context(session)
            result = await ability_registry.execute(tool_name, tool_args, context)

            if result.success:
                text = _format_tool_result(result.data, max_chars=max_chars)
            else:
                text = _truncate(result.error or "Error", max_chars=max_chars)
            session.add_tool_result(tool_id or "", text, name=tool_name)

            if skill_service is not None:
                try:
                    await skill_service.record_tool_run(
                        session_id=session.id,
                        tool_name=tool_name,
                        tool_call_id=tool_id,
                        arguments=tool_args,
                        success=result.success,
                        provider=provider_name,
                        model=options.model,
                        output=str(result.data) if result.success else "",
                        error=None if result.success else (result.error or "Error"),
                    )
                except Exception:
                    logger.exception("Failed to record tool run")

        messages: list[ProviderMessage] = []
        for item in session.get_context_messages():
            messages.append(
                ProviderMessage(
                    role=item.get("role", ""),
                    content=item.get("content", ""),
                    name=item.get("name"),
                    tool_calls=item.get("tool_calls"),
                    tool_call_id=item.get("tool_call_id"),
                ),
            )

        current = await ai_provider.chat(messages, options)

    return current.content or ""
