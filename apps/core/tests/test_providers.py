"""Tests for provider registry."""

import pytest
from apps.core.ai.providers.base import BaseProvider
from apps.core.ai.providers.openai_provider import OpenAIProvider
from apps.core.ai.providers.registry import ProviderRegistry
from apps.core.config.schemas import ProviderConfig


class TestProviderRegistry:
    """Test ProviderRegistry functionality."""

    def setup_method(self):
        """Reset registry before each test."""
        ProviderRegistry.clear()

    def test_register_provider_type(self):
        """Test registering a provider type."""

        class MockProvider(BaseProvider):
            name = "mock"
            available_models = ["mock-model"]

            async def chat(self, messages, options):
                pass

            async def stream_chat(self, messages, options):
                yield "mock"

        ProviderRegistry.register_type("mock", MockProvider)
        assert "mock" in ProviderRegistry._provider_types

    def test_list_types(self):
        """Test listing provider types."""
        # Register built-in types first
        ProviderRegistry._register_builtin_providers()
        types = ProviderRegistry.list_types()
        assert isinstance(types, list)
        assert "openai" in types

    def test_create_instance(self):
        """Test creating a provider instance manually."""
        # Need to register types first
        ProviderRegistry._register_builtin_providers()

        # Create instance with mock API key (won't actually connect)
        instance = ProviderRegistry.create_instance(
            provider_id="test-openai",
            provider_type="openai",
            api_key="test-key",
        )

        assert "test-openai" in ProviderRegistry._instances
        assert instance is not None

    def test_get_provider_not_initialized(self):
        """Test get returns None for non-existent provider when not loading from config."""
        ProviderRegistry._initialized = True  # Skip auto-loading
        result = ProviderRegistry.get("non-existent")
        assert result is None

    def test_list_instances_empty(self):
        """Test listing instances when empty."""
        ProviderRegistry._initialized = True  # Skip auto-loading
        instances = ProviderRegistry.list_instances()
        assert instances == []

    def test_set_default(self):
        """Test setting default provider."""
        ProviderRegistry._register_builtin_providers()

        # Create an instance first
        ProviderRegistry.create_instance(
            provider_id="test-default",
            provider_type="openai",
            api_key="test-key",
        )

        ProviderRegistry.set_default("test-default")
        assert ProviderRegistry._default_provider == "test-default"

    def test_set_default_not_instantiated(self):
        """Test setting default to non-existent provider raises error."""
        ProviderRegistry._initialized = True

        with pytest.raises(ValueError, match="not instantiated"):
            ProviderRegistry.set_default("non-existent")

    def test_clear(self):
        """Test clearing the registry."""
        ProviderRegistry._register_builtin_providers()
        ProviderRegistry.create_instance(
            provider_id="to-clear",
            provider_type="openai",
            api_key="test",
        )

        ProviderRegistry.clear()

        assert len(ProviderRegistry._instances) == 0
        assert ProviderRegistry._initialized is False

    def test_create_from_config_supports_common_aliases_and_ignores_unknown_keys(self):
        """Provider config should accept alias keys and ignore extras."""
        ProviderRegistry._register_builtin_providers()

        config = ProviderConfig(
            id="test-openai",
            type="openai",
            config={
                "api_key": "test-key",
                "api_base": "http://example.local/v1",
                "custom_extra_body": {"foo": "bar"},
                "unknown_key": "ignored",
            },
        )

        instance = ProviderRegistry._create_from_config(config)
        assert isinstance(instance, OpenAIProvider)
        assert instance.base_url == "http://example.local/v1"
        assert instance.extra_body == {"foo": "bar"}

    def test_create_from_config_supports_common_type_aliases_and_key_list(self):
        """Provider config should accept common type aliases and key lists."""
        ProviderRegistry._register_builtin_providers()

        config = ProviderConfig(
            id="test-openai-alias",
            type="openai_chat_completion",
            config={
                "key": ["test-key-1", "test-key-2"],
                "api_base": "http://example.local/v1",
            },
        )

        instance = ProviderRegistry._create_from_config(config)
        assert isinstance(instance, OpenAIProvider)
        assert instance.base_url == "http://example.local/v1"

    def test_create_from_config_normalizes_claude_thinking_alias(self):
        """Provider config should normalize thinking config keys for Claude."""
        ProviderRegistry._register_builtin_providers()
        if "claude" not in ProviderRegistry._provider_types:
            pytest.skip("Claude provider type not registered")

        from apps.core.ai.providers.claude_provider import ClaudeProvider

        thinking = {"type": "enabled", "budget_tokens": 1024}
        config = ProviderConfig(
            id="test-claude-alias",
            type="anthropic_chat_completion",
            config={
                "key": ["test-key"],
                "anth_thinking_config": thinking,
            },
        )

        instance = ProviderRegistry._create_from_config(config)
        assert isinstance(instance, ClaudeProvider)
        assert instance.thinking == thinking

    def test_create_from_config_normalizes_gemini_safety_settings_alias(self):
        """Provider config should normalize safety_settings keys for Gemini."""
        ProviderRegistry._register_builtin_providers()
        if "gemini" not in ProviderRegistry._provider_types:
            pytest.skip("Gemini provider type not registered")

        from apps.core.ai.providers.gemini_provider import GeminiProvider

        safety = {
            "harassment": "BLOCK_NONE",
            "hate_speech": "BLOCK_ONLY_HIGH",
        }
        config = ProviderConfig(
            id="test-gemini-alias",
            type="googlegenai_chat_completion",
            config={
                "key": ["test-key"],
                "gm_safety_settings": safety,
            },
        )

        instance = ProviderRegistry._create_from_config(config)
        assert isinstance(instance, GeminiProvider)
        assert instance._safety_settings == safety


class TestProviderRegistryAsync:
    """Async tests for ProviderRegistry."""

    def setup_method(self):
        """Reset registry before each test."""
        ProviderRegistry.clear()

    @pytest.mark.asyncio
    async def test_test_connection_no_provider(self):
        """Test connection test with non-existent provider."""
        ProviderRegistry._initialized = True  # Skip auto-loading
        result = await ProviderRegistry.test_connection("non-existent")
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_health_check_all_empty(self):
        """Test health check when no providers."""
        ProviderRegistry._initialized = True
        results = await ProviderRegistry.health_check_all()
        assert results == {}
