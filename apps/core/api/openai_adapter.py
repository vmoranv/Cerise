"""OpenAI-compatible adapter helpers."""

from __future__ import annotations

from apps.core.ai.dialogue.session import Session

from .openai_models import OpenAIChatMessage


def resolve_provider_model(model: str, *, default_provider: str) -> tuple[str, str]:
    """Resolve provider/model from OpenAI `model` field.

    Supported forms:
    - "provider_id/model_name"
    - "provider_id:model_name"
    - "model_name" (uses default_provider)
    """

    provider_id = default_provider
    model_name = model

    if "/" in model:
        provider_id, _, model_name = model.partition("/")
    elif ":" in model:
        provider_id, _, model_name = model.partition(":")

    provider_id = (provider_id or default_provider).strip()
    model_name = model_name.strip()

    if not provider_id:
        provider_id = default_provider
    if not model_name:
        model_name = model.strip()

    return provider_id, model_name


def normalize_stop(stop: str | list[str] | None) -> list[str] | None:
    if stop is None:
        return None
    if isinstance(stop, str):
        return [stop]
    return [item for item in stop if isinstance(item, str) and item]


def _require_text(value: object | None, *, field_name: str, allow_none: bool = False) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        raise ValueError(f"Only string content is supported for {field_name}")
    return value


def build_session_from_messages(
    messages: list[OpenAIChatMessage],
    *,
    session_id: str,
    user_id: str = "",
    default_system_prompt: str = "",
) -> tuple[Session, str]:
    """Build a Cerise Session from OpenAI messages.

    - All system messages are concatenated into Session.system_prompt.
    - The last message must be a user message; it is returned separately to
      avoid duplication when calling DialogueEngine.chat().
    """

    if not messages:
        raise ValueError("messages is required")

    last = messages[-1]
    if last.role != "user":
        raise ValueError("Last message must be role 'user'")

    last_content = _require_text(last.content, field_name="messages[-1].content")
    assert last_content is not None
    if not last_content.strip():
        raise ValueError("User message is empty")

    system_parts: list[str] = []
    if default_system_prompt:
        system_parts.append(default_system_prompt)

    for msg in messages:
        if msg.role != "system":
            continue
        content = _require_text(msg.content, field_name="system message content")
        assert content is not None
        if content.strip():
            system_parts.append(content)

    session = Session(
        id=session_id,
        user_id=user_id,
        system_prompt="\n\n".join(part for part in system_parts if part),
    )

    for msg in messages[:-1]:
        if msg.role == "system":
            continue

        content: str
        if msg.role == "assistant":
            content_value = _require_text(msg.content, field_name="assistant message content", allow_none=True)
            content = content_value or ""
        else:
            content_value = _require_text(msg.content, field_name=f"{msg.role} message content")
            content = content_value or ""

        session.add_message(
            msg.role,
            content,
            name=msg.name,
            tool_calls=msg.tool_calls,
            tool_call_id=msg.tool_call_id,
        )

    return session, last_content
