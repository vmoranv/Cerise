"""Dialogue event contracts."""

from __future__ import annotations

from typing import TypedDict

DIALOGUE_USER_MESSAGE = "dialogue.user_message"
DIALOGUE_ASSISTANT_RESPONSE = "dialogue.assistant_response"


class DialogueUserMessagePayload(TypedDict):
    session_id: str
    content: str


def build_dialogue_user_message(session_id: str, content: str) -> DialogueUserMessagePayload:
    return {"session_id": session_id, "content": content}


class DialogueAssistantResponsePayload(TypedDict):
    session_id: str
    content: str
    model: str


def build_dialogue_assistant_response(
    session_id: str,
    content: str,
    model: str,
) -> DialogueAssistantResponsePayload:
    return {"session_id": session_id, "content": content, "model": model}


__all__ = [
    "DIALOGUE_USER_MESSAGE",
    "DIALOGUE_ASSISTANT_RESPONSE",
    "DialogueUserMessagePayload",
    "DialogueAssistantResponsePayload",
    "build_dialogue_user_message",
    "build_dialogue_assistant_response",
]
