"""OpenAI-compatible request models.

These models intentionally accept and ignore extra fields so that OpenAI SDKs
and other compatible clients can call Cerise without strict schema coupling.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class OpenAIChatMessage(BaseModel):
    """Chat message in OpenAI-compatible format."""

    model_config = ConfigDict(extra="ignore")

    role: str
    content: Any | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class OpenAIChatCompletionsRequest(BaseModel):
    """ChatCompletions request subset."""

    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[OpenAIChatMessage]

    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop: str | list[str] | None = None

    n: int = 1

    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None

    user: str | None = None
