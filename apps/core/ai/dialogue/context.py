"""Dialogue context assembly helpers."""

from __future__ import annotations

import logging

from ...services.ports import MemoryService
from ..providers import Message as ProviderMessage
from .session import Session

logger = logging.getLogger(__name__)


def _prepend_memory_context(context: list[dict], memory_context: str) -> list[dict]:
    if not memory_context:
        return context
    memory_message = {"role": "system", "content": memory_context}
    if context and context[0].get("role") == "system":
        return [context[0], memory_message] + context[1:]
    return [memory_message] + context


async def build_context_messages(
    *,
    session: Session,
    query: str,
    memory_service: MemoryService | None,
    memory_recall: bool,
) -> list[ProviderMessage]:
    """Build provider messages with optional memory recall."""
    context = session.get_context_messages()
    memory_context = ""

    if memory_service and memory_recall:
        try:
            results = await memory_service.recall(
                query,
                limit=None,
                session_id=session.id,
            )
            memory_context = await memory_service.format_context(results, session_id=session.id)
        except Exception:  # pragma: no cover - recall is optional
            logger.exception("Memory recall failed")

    context = _prepend_memory_context(context, memory_context)
    messages: list[ProviderMessage] = []
    for item in context:
        messages.append(
            ProviderMessage(
                role=item.get("role", ""),
                content=item.get("content", ""),
                name=item.get("name"),
                tool_calls=item.get("tool_calls"),
                tool_call_id=item.get("tool_call_id"),
            )
        )
    return messages
