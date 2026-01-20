"""Tests for provider config schemas."""

from apps.core.config.schemas import ProviderConfig, ProvidersConfig


class TestProviderConfig:
    """Test ProviderConfig schema."""

    def test_create_provider_config(self):
        """Test creating a provider config."""
        config = ProviderConfig(
            id="openai-1",
            type="openai",
            name="OpenAI GPT-4",
            enabled=True,
            config={"api_key": "test-key", "default_model": "gpt-4o"},
        )
        assert config.id == "openai-1"
        assert config.type == "openai"
        assert config.enabled is True
        assert config.config["api_key"] == "test-key"


class TestProvidersConfig:
    """Test ProvidersConfig schema."""

    def test_create_providers_config(self):
        """Test creating providers config with list."""
        config = ProvidersConfig(
            default="openai-1",
            providers=[
                ProviderConfig(
                    id="openai-1",
                    type="openai",
                    name="OpenAI",
                    config={"api_key": "test"},
                )
            ],
        )
        assert config.default == "openai-1"
        assert len(config.providers) == 1
