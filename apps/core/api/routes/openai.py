"""OpenAI-compatible API routes.

This module provides a minimal subset of the OpenAI API surface so existing
OpenAI SDK clients can talk to Cerise with minimal changes.
"""

from __future__ import annotations

import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...ai import DialogueEngine
from ...config import get_config_loader
from ..dependencies import get_dialogue_engine
from ..openai_adapter import build_session_from_messages, normalize_stop, resolve_provider_model
from ..openai_models import OpenAIChatCompletionsRequest

router = APIRouter(prefix="/v1")


def _content_to_text(content: str | list[dict] | None) -> str:
    if content is None:
        return ""
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


def _estimate_tokens(text: str) -> int:
    # Rough estimate: 4 chars ~= 1 token
    if not text:
        return 0
    return max(0, len(text) // 4)


def _should_use_tools(request: OpenAIChatCompletionsRequest) -> bool:
    tool_choice = request.tool_choice
    if isinstance(tool_choice, str) and tool_choice.lower() == "none":
        return False
    if request.tools is not None:
        return len(request.tools) > 0
    if tool_choice is not None:
        return True
    return False


@router.get("/models")
async def list_models() -> dict:
    """List known models in OpenAI-compatible format."""

    loader = get_config_loader()
    app_config = loader.get_app_config()
    providers_config = loader.get_providers_config()

    models: list[dict] = []
    seen: set[str] = set()

    def add_model(model_id: str) -> None:
        if not model_id or model_id in seen:
            return
        seen.add(model_id)
        models.append(
            {
                "id": model_id,
                "object": "model",
                "owned_by": "cerise",
            }
        )

    default_provider = app_config.ai.default_provider or "default"
    default_model = app_config.ai.default_model or "default"
    add_model(f"{default_provider}/{default_model}")

    for provider in providers_config.providers:
        config = provider.config or {}
        model = config.get("model")
        if isinstance(model, str) and model:
            add_model(f"{provider.id}/{model}")

        models_list = config.get("models")
        if isinstance(models_list, list):
            for item in models_list:
                if isinstance(item, str) and item:
                    add_model(f"{provider.id}/{item}")

    # Best-effort: include provider-advertised models (may include defaults).
    try:
        from ...ai.providers import ProviderRegistry

        for provider_id in ProviderRegistry.list_instances():
            instance = ProviderRegistry.get(provider_id)
            if not instance:
                continue
            for model_name in instance.available_models:
                if isinstance(model_name, str) and model_name:
                    add_model(f"{provider_id}/{model_name}")
    except Exception:
        pass

    return {"object": "list", "data": models}


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: OpenAIChatCompletionsRequest,
    dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
) -> object:
    """OpenAI-compatible ChatCompletions endpoint."""

    if request.n != 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported")

    user_id = request.user or ""
    session_id = f"openai:{user_id}" if user_id else str(uuid4())

    try:
        session, user_message = build_session_from_messages(
            request.messages,
            session_id=session_id,
            user_id=user_id,
            default_system_prompt=getattr(dialogue_engine, "default_system_prompt", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    provider_id, model_name = resolve_provider_model(request.model, default_provider=dialogue_engine.default_provider)

    temperature = request.temperature
    top_p = request.top_p
    max_tokens = request.max_tokens
    stop = normalize_stop(request.stop)
    use_tools = _should_use_tools(request)

    response_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())

    if request.stream:

        async def event_stream():
            try:
                async for chunk in dialogue_engine.stream_chat(
                    session=session,
                    user_message=user_message,
                    provider=provider_id,
                    model=model_name,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stop=stop,
                ):
                    payload = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                payload = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                payload = {
                    "error": {
                        "message": str(exc),
                        "type": "server_error",
                    }
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        content = await dialogue_engine.chat(
            session=session,
            user_message=user_message,
            provider=provider_id,
            model=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            use_tools=use_tools,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompt_text_parts: list[str] = []
    if session.system_prompt:
        prompt_text_parts.append(session.system_prompt)
    prompt_messages = session.messages
    if prompt_messages and prompt_messages[-1].role == "assistant":
        prompt_messages = prompt_messages[:-1]
    prompt_text_parts.extend(_content_to_text(msg.content) for msg in prompt_messages)
    prompt_tokens = _estimate_tokens("\n".join(prompt_text_parts))
    completion_tokens = _estimate_tokens(content)

    return {
        "id": response_id,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
