"""
Provider Registry

Central registry for managing AI providers with configuration-driven loading.
"""

import contextlib
import logging
from typing import TYPE_CHECKING

from .base import BaseProvider, ChatOptions, Message

if TYPE_CHECKING:
    from ...config import ProviderConfig, ProvidersConfig

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for AI provider management with config-driven loading"""

    _provider_types: dict[str, type[BaseProvider]] = {}
    _instances: dict[str, BaseProvider] = {}
    _configs: dict[str, "ProviderConfig"] = {}
    _default_provider: str | None = None
    _initialized: bool = False

    @classmethod
    def register_type(cls, provider_type: str, provider_class: type[BaseProvider]) -> None:
        """Register a provider class by type name"""
        cls._provider_types[provider_type] = provider_class
        logger.info(f"Registered provider type: {provider_type}")

    @classmethod
    def register(cls, provider_class: type[BaseProvider]) -> None:
        """Register a provider class (uses class.name as type)"""
        name = provider_class.name  # type: ignore
        cls._provider_types[name] = provider_class
        logger.info(f"Registered provider: {name}")

    @classmethod
    def load_from_config(cls) -> None:
        """Load providers from configuration file"""
        from ...config import get_config_loader

        loader = get_config_loader()
        config = loader.get_providers_config()

        cls._load_providers_config(config)
        cls._initialized = True

    @classmethod
    def _load_providers_config(cls, config: "ProvidersConfig") -> None:
        """Internal: Load from ProvidersConfig"""
        # Register built-in providers
        cls._register_builtin_providers()

        for provider_config in config.providers:
            if not provider_config.enabled:
                continue

            cls._configs[provider_config.id] = provider_config

            try:
                cls._create_from_config(provider_config)
            except Exception as e:
                logger.warning(f"Failed to create provider {provider_config.id}: {e}")

        # Set default
        if config.default and config.default in cls._instances:
            cls._default_provider = config.default
        elif cls._instances:
            cls._default_provider = next(iter(cls._instances.keys()))

    @classmethod
    def _register_builtin_providers(cls) -> None:
        """Register built-in provider types"""
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
        from .rerank_providers import (
            BailianRerankProvider,
            VllmRerankProvider,
            XinferenceRerankProvider,
        )

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

        # Lazy import other providers
        with contextlib.suppress(ImportError):
            from .claude_provider import ClaudeProvider

            cls._provider_types["claude"] = ClaudeProvider
            cls._provider_types["anthropic"] = ClaudeProvider

        with contextlib.suppress(ImportError):
            from .gemini_provider import GeminiProvider

            cls._provider_types["gemini"] = GeminiProvider

    @classmethod
    def _create_from_config(cls, config: "ProviderConfig") -> BaseProvider:
        """Create provider instance from config"""
        provider_type = config.type

        if provider_type not in cls._provider_types:
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_class = cls._provider_types[provider_type]

        # Extract config parameters
        kwargs = config.config.copy()

        # Create instance
        instance = provider_class(**kwargs)
        cls._instances[config.id] = instance
        logger.info(f"Created provider: {config.id} (type={provider_type})")

        return instance

    @classmethod
    def create_instance(
        cls,
        provider_id: str,
        provider_type: str,
        **kwargs,
    ) -> BaseProvider:
        """Create and cache a provider instance manually"""
        if provider_type not in cls._provider_types:
            raise ValueError(f"Unknown provider type: {provider_type}")

        instance = cls._provider_types[provider_type](**kwargs)
        cls._instances[provider_id] = instance
        logger.info(f"Created provider instance: {provider_id}")

        return instance

    @classmethod
    def get(cls, provider_id: str) -> BaseProvider | None:
        """Get a cached provider instance by ID"""
        if not cls._initialized:
            cls.load_from_config()
        return cls._instances.get(provider_id)

    @classmethod
    def get_default(cls) -> BaseProvider | None:
        """Get the default provider"""
        if not cls._initialized:
            cls.load_from_config()
        if cls._default_provider:
            return cls.get(cls._default_provider)
        return None

    @classmethod
    def set_default(cls, provider_id: str) -> None:
        """Set the default provider"""
        if provider_id not in cls._instances:
            raise ValueError(f"Provider not instantiated: {provider_id}")
        cls._default_provider = provider_id

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered provider types"""
        return list(cls._provider_types.keys())

    @classmethod
    def list_instances(cls) -> list[str]:
        """List all instantiated providers"""
        if not cls._initialized:
            cls.load_from_config()
        return list(cls._instances.keys())

    @classmethod
    def list_providers(cls) -> list[str]:
        """Alias for list_instances for backward compatibility"""
        return cls.list_instances()

    @classmethod
    def get_provider_info(cls, provider_id: str) -> dict | None:
        """Get provider info including config and capabilities"""
        if provider_id not in cls._instances:
            return None

        instance = cls._instances[provider_id]
        config = cls._configs.get(provider_id)
        capabilities = instance.get_capabilities()

        return {
            "id": provider_id,
            "type": config.type if config else instance.name,
            "name": config.name if config else provider_id,
            "enabled": config.enabled if config else True,
            "models": instance.available_models,
            "capabilities": {
                "chat": capabilities.chat,
                "streaming": capabilities.streaming,
                "function_calling": capabilities.function_calling,
                "vision": capabilities.vision,
                "embeddings": capabilities.embeddings,
                "rerank": capabilities.rerank,
                "max_context_length": capabilities.max_context_length,
            },
        }

    @classmethod
    def _resolve_model_for_provider(cls, provider_id: str, instance: BaseProvider) -> str | None:
        """Pick a model using provider config first, then available models."""
        config = cls._configs.get(provider_id)
        if config:
            configured_model = config.config.get("model")
            if isinstance(configured_model, str) and configured_model:
                return configured_model
            configured_models = config.config.get("models")
            if isinstance(configured_models, list) and configured_models:
                first_model = configured_models[0]
                if isinstance(first_model, str) and first_model:
                    return first_model
        if instance.available_models:
            return instance.available_models[0]
        return None

    @classmethod
    async def test_connection(cls, provider_id: str) -> dict:
        """
        Test provider connection by sending a simple request.

        Returns:
            dict with status, latency_ms, and optional error
        """
        import time

        if provider_id not in cls._instances:
            return {"status": "error", "error": "Provider not found"}

        instance = cls._instances[provider_id]
        capabilities = instance.get_capabilities()
        if not capabilities.chat:
            if capabilities.embeddings:
                try:
                    await instance.embed(["ping"])
                    return {"status": "ok", "latency_ms": 0.0, "model": "embedding"}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            if capabilities.rerank:
                try:
                    await instance.rerank("ping", ["ping"])
                    return {"status": "ok", "latency_ms": 0.0, "model": "rerank"}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            return {"status": "error", "error": "Provider does not support chat/embed/rerank"}
        model = cls._resolve_model_for_provider(provider_id, instance)
        if not model:
            return {"status": "error", "error": "No model configured for provider"}

        try:
            start = time.perf_counter()

            # Send a minimal test message
            messages = [Message(role="user", content="Hi")]
            options = ChatOptions(
                model=model,
                max_tokens=5,
                temperature=0,
            )

            response = await instance.chat(messages, options)
            latency = (time.perf_counter() - start) * 1000

            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "model": response.model,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @classmethod
    async def health_check_all(cls) -> dict[str, bool]:
        """Check health of all providers"""
        results = {}
        for provider_id, instance in cls._instances.items():
            try:
                results[provider_id] = await instance.health_check()
            except Exception:
                results[provider_id] = False
        return results

    @classmethod
    def reload(cls) -> None:
        """Reload providers from configuration"""
        cls.clear()
        cls.load_from_config()

    @classmethod
    def clear(cls) -> None:
        """Clear all instances"""
        cls._instances.clear()
        cls._configs.clear()
        cls._default_provider = None
        cls._initialized = False
