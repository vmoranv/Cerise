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


def _require_content(
    value: object | None,
    *,
    field_name: str,
    allow_none: bool = False,
) -> str | list[dict] | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required")
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [item for item in value if isinstance(item, dict)]
        if parts:
            return parts
    raise ValueError(f"Only string or list content is supported for {field_name}")


def _content_has_user_value(content: str | list[dict] | None) -> bool:
    if content is None:
        return False
    if isinstance(content, str):
        return bool(content.strip())
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str) and item["text"].strip():
            return True
        if item.get("type") == "image_url":
            return True
    return False


def build_session_from_messages(
    messages: list[OpenAIChatMessage],
    *,
    session_id: str,
    user_id: str = "",
    default_system_prompt: str = "",
) -> tuple[Session, str | list[dict]]:
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

    last_content = _require_content(last.content, field_name="messages[-1].content")
    if not _content_has_user_value(last_content):
        raise ValueError("User message is empty")

    system_parts: list[str] = []
    if default_system_prompt:
        system_parts.append(default_system_prompt)

    for msg in messages:
        if msg.role != "system":
            continue
        content = _require_content(msg.content, field_name="system message content")
        if isinstance(content, str) and content.strip():
            system_parts.append(content)

    session = Session(
        id=session_id,
        user_id=user_id,
        system_prompt="\n\n".join(part for part in system_parts if part),
    )

    for msg in messages[:-1]:
        if msg.role == "system":
            continue

        content: str | list[dict]
        if msg.role == "assistant":
            content_value = _require_content(msg.content, field_name="assistant message content", allow_none=True)
            content = content_value or ""
        else:
            content_value = _require_content(msg.content, field_name=f"{msg.role} message content")
            content = content_value or ""

        session.add_message(
            msg.role,
            content,
            name=msg.name,
            tool_calls=msg.tool_calls,
            tool_call_id=msg.tool_call_id,
        )

    return session, last_content
