"""
Claude Provider

Provider implementation for Anthropic Claude API.
"""

from __future__ import annotations

import asyncio
import base64
import json
import random
from collections.abc import AsyncIterator
from mimetypes import guess_type

import httpx

from .base import (
    BaseProvider,
    ChatOptions,
    ChatResponse,
    Message,
    ProviderCapabilities,
)


class ClaudeProvider(BaseProvider):
    """Anthropic Claude API provider"""

    name = "claude"
    DEFAULT_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        models: list[str] | None = None,
        thinking: dict | None = None,
        timeout: float | None = None,
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
            raise ValueError("Claude provider requires api_key or api_keys")

        self._api_keys = keys
        self._available_models = models or self.DEFAULT_MODELS
        self.base_url = base_url
        self.thinking = thinking if isinstance(thinking, dict) and thinking else None
        self.timeout = timeout

        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self.retry_jitter = max(0.0, float(retry_jitter))
        self._key_index = 0
        self._rng = random.Random()
        self._lock = asyncio.Lock()
        self._clients: dict[str, object] = {}

    @property
    def available_models(self) -> list[str]:
        return self._available_models

    def _get_current_key(self) -> str:
        if not self._api_keys:
            return ""
        return self._api_keys[self._key_index]

    def _rotate_key(self) -> None:
        if len(self._api_keys) <= 1:
            return
        self._key_index = (self._key_index + 1) % len(self._api_keys)

    def _get_client(self, api_key: str):
        client = self._clients.get(api_key)
        if client is not None:
            return client

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            api_key=api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        self._clients[api_key] = client
        return client

    def _classify_error(self, exc: Exception) -> tuple[bool, bool]:
        try:
            from anthropic import (
                APIConnectionError,
                APITimeoutError,
                AuthenticationError,
                InternalServerError,
                RateLimitError,
            )
        except Exception:
            return False, False

        if isinstance(exc, (APITimeoutError, APIConnectionError, InternalServerError)):
            return True, False
        if isinstance(exc, (RateLimitError, AuthenticationError)):
            return True, True
        return False, False

    async def _sleep_backoff(self, attempt: int) -> None:
        if self.retry_backoff <= 0:
            return
        base = self.retry_backoff * (2**attempt)
        jitter = self._rng.random() * self.retry_jitter if self.retry_jitter else 0.0
        await asyncio.sleep(base + jitter)

    async def _call_with_retry(self, fn):
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            async with self._lock:
                api_key = self._get_current_key()
                client = self._get_client(api_key)

            try:
                return await fn(client)
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

    @staticmethod
    def _openai_tool_to_anthropic(tool: dict) -> dict | None:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(fn, dict):
            return None
        name = fn.get("name")
        if not isinstance(name, str) or not name:
            return None
        description = fn.get("description")
        parameters = fn.get("parameters")
        payload = {
            "name": name,
            "description": description if isinstance(description, str) else "",
            "input_schema": parameters if isinstance(parameters, dict) else {"type": "object", "properties": {}},
        }
        return payload

    async def _openai_parts_to_anthropic_blocks(self, parts: list[dict]) -> list[dict]:
        blocks: list[dict] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str) and text:
                    blocks.append({"type": "text", "text": text})
            elif part.get("type") == "image_url":
                image_url = part.get("image_url")
                url: str | None = None
                if isinstance(image_url, dict):
                    url_value = image_url.get("url")
                    url = url_value if isinstance(url_value, str) else None
                elif isinstance(image_url, str):
                    url = image_url
                if not url:
                    blocks.append({"type": "text", "text": "[image]"})
                    continue
                image_block = await self._image_url_to_anthropic_block(url)
                blocks.append(image_block or {"type": "text", "text": "[image]"})
        return blocks or [{"type": "text", "text": " "}]

    async def _image_url_to_anthropic_block(self, url: str) -> dict | None:
        url = url.strip()
        if not url:
            return None

        # data URI
        if url.startswith("data:") and "base64," in url:
            header, b64data = url.split("base64,", 1)
            media_type = header.removeprefix("data:").split(";", 1)[0].strip() or "image/jpeg"
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64data,
                },
            }

        # local file
        file_path = url
        if url.startswith("file://"):
            file_path = url.removeprefix("file://").lstrip("/")
        if not url.startswith("http"):
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
            except OSError:
                return None
            mime_type, _ = guess_type(file_path)
            media_type = mime_type or "image/jpeg"
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(data).decode("utf-8"),
                },
            }

        # remote url
        try:
            async with httpx.AsyncClient(timeout=self.timeout or 30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.content
                media_type = resp.headers.get("content-type", "").split(";", 1)[0].strip() or "image/jpeg"
        except Exception:
            return None

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(data).decode("utf-8"),
            },
        }

    async def _assistant_content(self, message: Message) -> str | list[dict]:
        blocks: list[dict] = []
        if isinstance(message.content, str):
            if message.content:
                blocks.append({"type": "text", "text": message.content})
        else:
            blocks.extend(await self._openai_parts_to_anthropic_blocks(message.content))

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                tool_id = tool_call.get("id")
                fn = tool_call.get("function", {})
                if not isinstance(tool_id, str) or not tool_id:
                    continue
                if not isinstance(fn, dict):
                    continue
                name = fn.get("name")
                args = fn.get("arguments", {})
                if not isinstance(name, str) or not name:
                    continue
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if not isinstance(args, dict):
                    args = {}
                blocks.append({"type": "tool_use", "id": tool_id, "name": name, "input": args})

        if blocks:
            return blocks
        return self._content_to_text(message.content)

    async def _build_payload(self, messages: list[Message]) -> tuple[str, list[dict]]:
        system_parts: list[str] = []
        out_messages: list[dict] = []

        for message in messages:
            if message.role == "system":
                system_parts.append(self._content_to_text(message.content))
                continue

            if message.role == "tool":
                tool_use_id = message.tool_call_id
                tool_text = self._content_to_text(message.content)
                if not tool_use_id:
                    out_messages.append({"role": "user", "content": tool_text})
                else:
                    out_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": tool_text,
                                }
                            ],
                        }
                    )
                continue

            role = message.role if message.role in {"user", "assistant"} else "user"
            if role == "assistant":
                content = await self._assistant_content(message)
            else:
                content = (
                    message.content
                    if isinstance(message.content, str)
                    else await self._openai_parts_to_anthropic_blocks(message.content)
                )
            out_messages.append({"role": role, "content": content})

        system_prompt = "\n\n".join(part for part in system_parts if part)
        return system_prompt, out_messages

    async def chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> ChatResponse:
        """Chat completion"""
        system_msg, chat_messages = await self._build_payload(messages)

        anthropic_tools: list[dict] | None = None
        if options.tools:
            converted = [self._openai_tool_to_anthropic(tool) for tool in options.tools]
            anthropic_tools = [tool for tool in converted if tool is not None]

        payload: dict = {
            "model": options.model,
            "max_tokens": options.max_tokens,
            "system": system_msg or "",
            "messages": chat_messages,
        }
        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.stop:
            payload["stop_sequences"] = options.stop
        if anthropic_tools:
            payload["tools"] = anthropic_tools
        if self.thinking:
            payload["thinking"] = self.thinking

        async def _do_request(client):
            return await client.messages.create(**payload)

        response = await self._call_with_retry(_do_request)

        text_parts: list[str] = []
        tool_calls: list[dict] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(getattr(block, "text", "") or "")
            elif block_type == "tool_use":
                tool_id = getattr(block, "id", "") or ""
                name = getattr(block, "name", "") or ""
                tool_input = getattr(block, "input", {}) or {}
                if tool_id and name:
                    tool_calls.append(
                        {
                            "id": tool_id,
                            "type": "function",
                            "function": {"name": name, "arguments": tool_input},
                        }
                    )

        return ChatResponse(
            content="".join(text_parts),
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
            },
            tool_calls=tool_calls or None,
            finish_reason=response.stop_reason or "stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Streaming chat completion"""
        system_msg, chat_messages = await self._build_payload(messages)

        payload = {
            "model": options.model,
            "max_tokens": options.max_tokens,
            "system": system_msg or "",
            "messages": chat_messages,
        }
        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.stop:
            payload["stop_sequences"] = options.stop
        if self.thinking:
            payload["thinking"] = self.thinking

        async def _do_request(client):
            return client.messages.stream(**payload)

        stream = await self._call_with_retry(_do_request)
        async with stream as ctx:
            async for text in ctx.text_stream:
                yield text

    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities"""
        return ProviderCapabilities(
            streaming=True,
            function_calling=True,
            vision=True,
            max_context_length=200000,
        )
