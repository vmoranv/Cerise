"""
Provider registry configuration helpers.
"""

import contextlib
import logging
from typing import TYPE_CHECKING

from .base import BaseProvider

if TYPE_CHECKING:
    from ...config import ProviderConfig, ProvidersConfig

logger = logging.getLogger(__name__)


class ProviderRegistryConfigMixin:
    _provider_types: dict[str, type[BaseProvider]]
    _instances: dict[str, BaseProvider]
    _configs: dict[str, "ProviderConfig"]
    _default_provider: str | None
    _initialized: bool

    @classmethod
    def register_type(cls, provider_type: str, provider_class: type[BaseProvider]) -> None:
        """Register a provider class by type name."""
        cls._provider_types[provider_type] = provider_class
        logger.info("Registered provider type: %s", provider_type)

    @classmethod
    def register(cls, provider_class: type[BaseProvider]) -> None:
        """Register a provider class (uses class.name as type)."""
        name = provider_class.name  # type: ignore
        cls._provider_types[name] = provider_class
        logger.info("Registered provider: %s", name)

    @classmethod
    def load_from_config(cls) -> None:
        """Load providers from configuration file."""
        from ...config import get_config_loader

        loader = get_config_loader()
        config = loader.get_providers_config()

        cls._load_providers_config(config)
        cls._initialized = True

    @classmethod
    def _load_providers_config(cls, config: "ProvidersConfig") -> None:
        """Internal: Load from ProvidersConfig."""
        cls._register_builtin_providers()

        for provider_config in config.providers:
            if not provider_config.enabled:
                continue

            cls._configs[provider_config.id] = provider_config

            try:
                cls._create_from_config(provider_config)
            except Exception as exc:
                logger.warning("Failed to create provider %s: %s", provider_config.id, exc)

        if config.default and config.default in cls._instances:
            cls._default_provider = config.default
        elif cls._instances:
            cls._default_provider = next(iter(cls._instances.keys()))

    @classmethod
    def _register_builtin_providers(cls) -> None:
        """Register built-in provider types."""
        from .compat_providers import (
            DeepSeekProvider,
            FireworksProvider,
            GroqProvider,
            LMStudioProvider,
            MistralProvider,
            MoonshotProvider,
            OllamaProvider,
            OpenRouterProvider,
            QwenProvider,
            TogetherProvider,
            XAIProvider,
            ZhipuProvider,
        )
        from .embedding_providers import GeminiEmbeddingProvider, OpenAIEmbeddingProvider
        from .openai_provider import OpenAIProvider
        from .rerank_http_provider import RerankHttpProvider
        from .rerank_providers import BailianRerankProvider, VllmRerankProvider, XinferenceRerankProvider
        from .zerolan_provider import ZerolanProvider

        cls._provider_types["openai"] = OpenAIProvider
        cls._provider_types["rerank_http"] = RerankHttpProvider
        cls._provider_types["openai_embedding"] = OpenAIEmbeddingProvider
        cls._provider_types["gemini_embedding"] = GeminiEmbeddingProvider
        cls._provider_types["vllm_rerank"] = VllmRerankProvider
        cls._provider_types["xinference_rerank"] = XinferenceRerankProvider
        cls._provider_types["bailian_rerank"] = BailianRerankProvider
        cls._provider_types["groq"] = GroqProvider
        cls._provider_types["xai"] = XAIProvider
        cls._provider_types["zhipu"] = ZhipuProvider
        cls._provider_types["deepseek"] = DeepSeekProvider
        cls._provider_types["moonshot"] = MoonshotProvider
        cls._provider_types["qwen"] = QwenProvider
        cls._provider_types["mistral"] = MistralProvider
        cls._provider_types["together"] = TogetherProvider
        cls._provider_types["fireworks"] = FireworksProvider
        cls._provider_types["openrouter"] = OpenRouterProvider
        cls._provider_types["ollama"] = OllamaProvider
        cls._provider_types["lmstudio"] = LMStudioProvider
        cls._provider_types["zerolan"] = ZerolanProvider

        with contextlib.suppress(ImportError):
            from .claude_provider import ClaudeProvider

            cls._provider_types["claude"] = ClaudeProvider
            cls._provider_types["anthropic"] = ClaudeProvider

        with contextlib.suppress(ImportError):
            from .gemini_provider import GeminiProvider

            cls._provider_types["gemini"] = GeminiProvider

    @classmethod
    def _create_from_config(cls, config: "ProviderConfig") -> BaseProvider:
        """Create provider instance from config."""
        provider_type = config.type

        if provider_type not in cls._provider_types:
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_class = cls._provider_types[provider_type]
        kwargs = config.config.copy()

        instance = provider_class(**kwargs)
        cls._instances[config.id] = instance
        logger.info("Created provider: %s (type=%s)", config.id, provider_type)

        return instance
