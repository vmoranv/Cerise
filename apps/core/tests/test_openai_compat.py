"""Tests for OpenAI-compatible API routes."""

from __future__ import annotations

import json
from types import SimpleNamespace

from apps.core.api.routes.openai import router as openai_router
from apps.core.config import loader as loader_module
from fastapi import FastAPI
from fastapi.testclient import TestClient


class DummyDialogueEngine:
    default_provider = "default-provider"
    default_model = "default-model"
    default_system_prompt = "DEFAULT SYSTEM PROMPT"

    def __init__(self) -> None:
        self.last_call: dict | None = None

    async def chat(
        self,
        *,
        session,
        user_message: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        use_tools: bool = False,
    ) -> str:
        self.last_call = {
            "session_id": session.id,
            "user_message": user_message,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stop": stop,
            "use_tools": use_tools,
        }
        return "hello"

    async def stream_chat(
        self,
        *,
        session,
        user_message: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
    ):
        yield "he"
        yield "llo"


def _make_app(engine: DummyDialogueEngine) -> FastAPI:
    app = FastAPI()
    app.state.services = SimpleNamespace(dialogue_engine=engine)
    app.include_router(openai_router)
    return app


def _reset_config_loader(monkeypatch, data_dir) -> None:
    monkeypatch.setenv("CERISE_DATA_DIR", str(data_dir))
    loader_module._loader = None


def test_chat_completions_non_stream_happy_path() -> None:
    engine = DummyDialogueEngine()
    app = _make_app(engine)

    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "testprov/m1",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "hello"
    assert engine.last_call is not None
    assert engine.last_call["provider"] == "testprov"
    assert engine.last_call["model"] == "m1"


def test_chat_completions_requires_user_message() -> None:
    engine = DummyDialogueEngine()
    app = _make_app(engine)

    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "testprov/m1",
                "messages": [{"role": "assistant", "content": "hi"}],
            },
        )

    assert resp.status_code == 400


def test_chat_completions_stream_sse_format() -> None:
    engine = DummyDialogueEngine()
    app = _make_app(engine)

    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "testprov/m1",
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    data_lines = [line for line in resp.text.splitlines() if line.startswith("data: ")]
    assert data_lines, "expected SSE data lines"
    assert data_lines[-1] == "data: [DONE]"

    payloads = [json.loads(line[6:]) for line in data_lines[:-1] if line[6:] != "[DONE]"]
    assert payloads[0]["choices"][0]["delta"]["content"] == "he"
    assert payloads[1]["choices"][0]["delta"]["content"] == "llo"


def test_models_endpoint_returns_default_model_even_without_providers_yaml(tmp_path, monkeypatch) -> None:
    _reset_config_loader(monkeypatch, tmp_path)
    engine = DummyDialogueEngine()
    app = _make_app(engine)

    with TestClient(app) as client:
        resp = client.get("/v1/models")

    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    model_ids = {item["id"] for item in data["data"]}
    assert "openai/gpt-4o" in model_ids
