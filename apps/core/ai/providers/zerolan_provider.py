"""ZerolanCore HTTP provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from .base import BaseProvider, ChatOptions, ChatResponse, Message, ProviderCapabilities


class ZerolanProvider(BaseProvider):
    """Provider for ZerolanCore LLM HTTP endpoints."""

    name = "zerolan"

    def __init__(
        self,
        base_url: str = "http://localhost:11002",
        timeout: float | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or 30.0
        self._model = model or "default"
        self._client: httpx.AsyncClient | None = None

    @property
    def available_models(self) -> list[str]:
        return [self._model] if self._model else []

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _predict_url(self) -> str:
        if self.base_url.endswith("/llm/predict"):
            return self.base_url
        return f"{self.base_url}/llm/predict"

    def _split_history(self, messages: list[Message]) -> tuple[str, list[dict]]:
        cleaned = [m for m in messages if m.role in {"system", "user", "assistant"}]
        if not cleaned:
            return "", []

        last_user_idx = None
        for idx in range(len(cleaned) - 1, -1, -1):
            if cleaned[idx].role == "user":
                last_user_idx = idx
                break
        if last_user_idx is None:
            last_user_idx = len(cleaned) - 1

        text = self._normalize_text(cleaned[last_user_idx].content)
        history = [
            {"role": msg.role, "content": self._normalize_text(msg.content), "metadata": None}
            for msg in cleaned[:last_user_idx]
        ]
        return text, history

    @staticmethod
    def _normalize_text(content: str | list[dict]) -> str:
        if isinstance(content, str):
            return content
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif item.get("type") == "image_url":
                parts.append("[image]")
        return "\n".join(parts).strip()

    async def chat(self, messages: list[Message], options: ChatOptions) -> ChatResponse:
        text, history = self._split_history(messages)
        payload = {"text": text, "history": history}

        response = await self.client.post(self._predict_url(), json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("response") or data.get("content") or ""

        return ChatResponse(
            content=content,
            model=options.model,
        )

    async def stream_chat(self, messages: list[Message], options: ChatOptions) -> AsyncIterator[str]:
        response = await self.chat(messages, options)
        yield response.content

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=False,
            function_calling=False,
            vision=False,
        )
