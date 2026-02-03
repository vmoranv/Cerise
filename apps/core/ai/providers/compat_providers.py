"""
OpenAI-compatible providers for popular vendors.
"""

from __future__ import annotations

from .openai_provider import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """Base class for OpenAI-compatible endpoints."""

    DEFAULT_BASE_URL: str | None = None
    DEFAULT_MODELS: list[str] = []

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        models: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(
            api_key=api_key,
            api_keys=api_keys,
            base_url=base_url or self.DEFAULT_BASE_URL,
            models=models or self.DEFAULT_MODELS,
            **kwargs,
        )


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODELS = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ]


class XAIProvider(OpenAICompatibleProvider):
    name = "xai"
    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODELS = [
        "grok-2",
        "grok-2-mini",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        xai_native_search: bool = False,
        **kwargs,
    ):
        self.xai_native_search = xai_native_search
        super().__init__(api_key=api_key, api_keys=api_keys, **kwargs)

    def _build_extra_body(self) -> dict:
        extra = super()._build_extra_body()
        if self.xai_native_search:
            extra["search_parameters"] = {"mode": "auto"}
        return extra


class ZhipuProvider(OpenAICompatibleProvider):
    name = "zhipu"
    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODELS = [
        "glm-4",
        "glm-4v",
    ]


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODELS = [
        "deepseek-chat",
        "deepseek-reasoner",
    ]


class MoonshotProvider(OpenAICompatibleProvider):
    name = "moonshot"
    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
    DEFAULT_MODELS = [
        "moonshot-v1-8k",
        "moonshot-v1-32k",
        "moonshot-v1-128k",
    ]


class QwenProvider(OpenAICompatibleProvider):
    name = "qwen"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODELS = [
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
    ]


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"
    DEFAULT_BASE_URL = "https://api.mistral.ai/v1"
    DEFAULT_MODELS = [
        "mistral-large-latest",
        "mistral-small-latest",
    ]


class TogetherProvider(OpenAICompatibleProvider):
    name = "together"
    DEFAULT_BASE_URL = "https://api.together.xyz/v1"
    DEFAULT_MODELS = [
        "meta-llama/Llama-3.1-70B-Instruct-Turbo",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
    ]


class FireworksProvider(OpenAICompatibleProvider):
    name = "fireworks"
    DEFAULT_BASE_URL = "https://api.fireworks.ai/inference/v1"
    DEFAULT_MODELS = [
        "accounts/fireworks/models/llama-v3p1-70b-instruct",
        "accounts/fireworks/models/mixtral-8x7b-instruct",
    ]


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODELS = [
        "openrouter/auto",
    ]


class OllamaProvider(OpenAICompatibleProvider):
    name = "ollama"
    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODELS = [
        "llama3.1",
    ]


class LMStudioProvider(OpenAICompatibleProvider):
    name = "lmstudio"
    DEFAULT_BASE_URL = "http://localhost:1234/v1"
    DEFAULT_MODELS = []
