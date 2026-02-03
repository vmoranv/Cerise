"""
Gemini Provider

Provider implementation for Google Gemini API.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator

from .base import (
    BaseProvider,
    ChatOptions,
    ChatResponse,
    Message,
    ProviderCapabilities,
)


class GeminiProvider(BaseProvider):
    """Google Gemini API provider"""

    name = "gemini"
    DEFAULT_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        models: list[str] | None = None,
        safety_settings: dict[str, str] | None = None,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        retry_jitter: float = 0.1,
    ) -> None:
        keys: list[str] = []
        if isinstance(api_keys, list):
            keys.extend([item for item in api_keys if isinstance(item, str) and item.strip()])
        if isinstance(api_key, str) and api_key.strip():
            keys.insert(0, api_key)
        if not keys:
            raise ValueError("Gemini provider requires api_key or api_keys")

        self._api_keys = keys
        self._key_index = 0
        self._rng = random.Random()
        self._lock = asyncio.Lock()

        self._available_models = models or self.DEFAULT_MODELS
        self._safety_settings = safety_settings or {}
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self.retry_jitter = max(0.0, float(retry_jitter))
        self._client = None

    @property
    def available_models(self) -> list[str]:
        return self._available_models

    @property
    def client(self):
        """Lazy load Gemini client"""
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self._api_keys[self._key_index])
            self._client = genai
        return self._client

    def _rotate_key(self) -> None:
        if len(self._api_keys) <= 1:
            return
        self._key_index = (self._key_index + 1) % len(self._api_keys)
        if self._client is not None:
            self._client.configure(api_key=self._api_keys[self._key_index])

    @staticmethod
    def _content_to_text(content: str | list[dict] | None) -> str:
        if content is None:
            return ""
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

    def _build_safety_settings(self) -> list | None:
        if not self._safety_settings:
            return None
        try:
            from google.generativeai.types import HarmBlockThreshold, HarmCategory
        except Exception:
            return None

        category_map = {
            "harassment": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "hate_speech": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "sexually_explicit": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "dangerous_content": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        }
        threshold_map = {
            "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
            "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        }

        settings = []
        for key, value in self._safety_settings.items():
            category = category_map.get(key)
            threshold = threshold_map.get(str(value))
            if category and threshold:
                settings.append({"category": category, "threshold": threshold})
        return settings or None

    def _classify_error(self, exc: Exception) -> tuple[bool, bool]:
        message = str(exc)
        # Best-effort classification based on common Gemini error strings.
        if "429" in message or "rate limit" in message.lower():
            return True, True
        if "API key not valid" in message or "invalid" in message.lower() and "key" in message.lower():
            return True, True
        return True, False

    async def _sleep_backoff(self, attempt: int) -> None:
        if self.retry_backoff <= 0:
            return
        base = self.retry_backoff * (2**attempt)
        jitter = self._rng.random() * self.retry_jitter if self.retry_jitter else 0.0
        await asyncio.sleep(base + jitter)

    async def _call_with_retry(self, fn):
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with self._lock:
                    return await fn()
            except Exception as exc:
                last_exc = exc
                retryable, rotate = self._classify_error(exc)
                if not retryable or attempt >= self.max_retries:
                    raise
                if rotate:
                    async with self._lock:
                        self._rotate_key()
                await self._sleep_backoff(attempt)
        assert last_exc is not None
        raise last_exc

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        # Convert messages to Gemini format
        history = []
        system_parts: list[str] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(self._content_to_text(msg.content))
            elif msg.role == "user":
                history.append({"role": "user", "parts": [self._content_to_text(msg.content)]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [self._content_to_text(msg.content)]})

        system_instruction = "\n\n".join(part for part in system_parts if part) or None
        safety_settings = self._build_safety_settings()

        # Start chat with system instruction if provided
        model = self.client.GenerativeModel(
            options.model, system_instruction=system_instruction, safety_settings=safety_settings
        )
        chat = model.start_chat(history=history[:-1] if history else [])

        # Get last user message
        last_msg = history[-1]["parts"][0] if history else ""

        async def _do_request():
            generation_config: dict = {
                "temperature": options.temperature,
                "max_output_tokens": options.max_tokens,
                "top_p": options.top_p,
            }
            if options.stop:
                generation_config["stop_sequences"] = options.stop
            return await chat.send_message_async(last_msg, generation_config=generation_config)

        response = await self._call_with_retry(_do_request)

        return ChatResponse(
            content=response.text,
            model=options.model,
            usage={},  # Gemini doesn't provide token counts easily
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Streaming chat completion"""
        history = []
        system_parts: list[str] = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(self._content_to_text(msg.content))
            if msg.role == "user":
                history.append({"role": "user", "parts": [self._content_to_text(msg.content)]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [self._content_to_text(msg.content)]})

        system_instruction = "\n\n".join(part for part in system_parts if part) or None
        safety_settings = self._build_safety_settings()
        model = self.client.GenerativeModel(
            options.model, system_instruction=system_instruction, safety_settings=safety_settings
        )
        chat = model.start_chat(history=history[:-1] if history else [])
        last_msg = history[-1]["parts"][0] if history else ""

        async def _do_request():
            generation_config: dict = {
                "temperature": options.temperature,
                "max_output_tokens": options.max_tokens,
                "top_p": options.top_p,
            }
            if options.stop:
                generation_config["stop_sequences"] = options.stop
            return await chat.send_message_async(last_msg, generation_config=generation_config, stream=True)

        response = await self._call_with_retry(_do_request)

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities"""
        return ProviderCapabilities(
            streaming=True,
            function_calling=False,
            vision=False,
            max_context_length=1000000,  # Gemini 1.5 supports 1M tokens
        )
