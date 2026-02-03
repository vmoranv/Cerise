"""
Provider registry configuration helpers.
"""

import contextlib
import inspect
import logging
from typing import TYPE_CHECKING

from .base import BaseProvider

if TYPE_CHECKING:
    from ...config import ProviderConfig, ProvidersConfig

logger = logging.getLogger(__name__)


def _apply_alias(kwargs: dict, *, src: str, dest: str) -> None:
    if src not in kwargs or dest in kwargs:
        return
    kwargs[dest] = kwargs.pop(src)


def _normalize_provider_kwargs(provider_type: str, kwargs: dict) -> dict:
    """Normalize provider config keys from common external templates.

    This keeps Cerise config compatible with common community config field
    names without requiring exact key matches.

    Note: We still validate required fields by letting provider constructors
    raise if a required argument is missing.
    """

    normalized = dict(kwargs)

    # Common aliases used by other projects/templates.
    _apply_alias(normalized, src="api_base", dest="base_url")
    _apply_alias(normalized, src="api_base_url", dest="base_url")
    _apply_alias(normalized, src="custom_extra_body", dest="extra_body")

    # Embedding provider aliases (common).
    _apply_alias(normalized, src="embedding_api_key", dest="api_key")
    _apply_alias(normalized, src="embedding_api_base", dest="base_url")
    _apply_alias(normalized, src="embedding_model", dest="model")

    # Rerank provider aliases (common).
    _apply_alias(normalized, src="rerank_api_key", dest="api_key")
    _apply_alias(normalized, src="rerank_api_base", dest="base_url")
    _apply_alias(normalized, src="rerank_model", dest="model")

    timeout = normalized.get("timeout")
    if isinstance(timeout, str):
        with contextlib.suppress(ValueError, TypeError):
            normalized["timeout"] = float(timeout)

    if provider_type == "openai":
        organization = normalized.get("organization")
        if organization is None:
            _apply_alias(normalized, src="org", dest="organization")

    return normalized


def _filter_kwargs_for_provider(
    provider_id: str, provider_type: str, provider_class: type[BaseProvider], kwargs: dict
) -> dict:
    """Drop unexpected kwargs to avoid hard failures on extra config keys."""

    signature = inspect.signature(provider_class.__init__)
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        return kwargs

    allowed: set[str] = set()
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }:
            allowed.add(name)

    unknown = sorted(key for key in kwargs if key not in allowed)
    if unknown:
        logger.warning(
            "Ignoring unknown config keys for provider %s (type=%s): %s",
            provider_id,
            provider_type,
            ", ".join(unknown),
        )

    return {key: value for key, value in kwargs.items() if key in allowed}


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
        kwargs = _normalize_provider_kwargs(provider_type, config.config.copy())
        kwargs = _filter_kwargs_for_provider(config.id, provider_type, provider_class, kwargs)

        instance = provider_class(**kwargs)
        cls._instances[config.id] = instance
        logger.info("Created provider: %s (type=%s)", config.id, provider_type)

        return instance
