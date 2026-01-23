"""Tests for ConfigLoader functionality."""

import os
import tempfile
from pathlib import Path

import yaml
from apps.core.config.loader import ConfigLoader
from apps.core.config.schemas import AIConfig, AppConfig, ProviderConfig, ProvidersConfig, ServerConfig


def _prepare_data_dir(tmpdir: str) -> Path:
    data_dir = Path(tmpdir)
    for name in ["plugins", "characters", "logs", "cache"]:
        (data_dir / name).mkdir()
    return data_dir


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    def test_load_app_config_from_file(self):
        """Test loading app config from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)

            config_file = data_dir / "config.yaml"
            config_data = {
                "server": {"host": "localhost", "port": 3000},
                "ai": {"default_provider": "gemini"},
            }
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            loader = ConfigLoader(data_dir)
            config = loader.load_app_config()
            assert config.server.host == "localhost"
            assert config.server.port == 3000
            assert config.ai.default_provider == "gemini"

    def test_load_providers_config_from_file(self):
        """Test loading providers config from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)

            providers_file = data_dir / "providers.yaml"
            providers_data = {
                "default": "openai-1",
                "providers": [
                    {
                        "id": "openai-1",
                        "type": "openai",
                        "name": "OpenAI",
                        "enabled": True,
                        "config": {"api_key": "sk-test"},
                    }
                ],
            }
            with open(providers_file, "w") as f:
                yaml.dump(providers_data, f)

            loader = ConfigLoader(data_dir)
            config = loader.load_providers_config()
            assert len(config.providers) == 1
            assert config.providers[0].id == "openai-1"
            assert config.providers[0].type == "openai"

    def test_save_app_config(self):
        """Test saving app config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)
            loader = ConfigLoader(data_dir)

            config = AppConfig(
                server=ServerConfig(port=5000),
                ai=AIConfig(default_provider="claude"),
            )
            loader.save_app_config(config)

            loaded = loader.load_app_config()
            assert loaded.server.port == 5000
            assert loaded.ai.default_provider == "claude"

    def test_save_providers_config(self):
        """Test saving providers config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)
            loader = ConfigLoader(data_dir)

            config = ProvidersConfig(
                default="test-1",
                providers=[
                    ProviderConfig(
                        id="test-1",
                        type="openai",
                        name="Test Provider",
                        enabled=True,
                        config={"api_key": "test"},
                    )
                ],
            )
            loader.save_providers_config(config)

            loaded = loader.load_providers_config()
            assert len(loaded.providers) == 1
            assert loaded.providers[0].id == "test-1"

    def test_add_provider(self):
        """Test adding a provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)
            loader = ConfigLoader(data_dir)

            provider = ProviderConfig(
                id="new-provider",
                type="openai",
                name="New Provider",
                config={"api_key": "test"},
            )
            loader.add_provider(provider)

            config = loader.get_providers_config()
            assert any(p.id == "new-provider" for p in config.providers)

    def test_remove_provider(self):
        """Test removing a provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)
            loader = ConfigLoader(data_dir)

            provider = ProviderConfig(
                id="to-remove",
                type="openai",
                name="To Remove",
                config={"api_key": "test"},
            )
            loader.add_provider(provider)

            result = loader.remove_provider("to-remove")
            assert result is True

            config = loader.get_providers_config()
            assert not any(p.id == "to-remove" for p in config.providers)

    def test_expand_env_vars(self):
        """Test environment variable expansion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)

            os.environ["TEST_API_KEY"] = "secret-key-123"

            providers_file = data_dir / "providers.yaml"
            providers_data = {
                "default": "test-1",
                "providers": [
                    {
                        "id": "test-1",
                        "type": "openai",
                        "name": "Test",
                        "enabled": True,
                        "config": {"api_key": "${TEST_API_KEY}"},
                    }
                ],
            }
            with open(providers_file, "w") as f:
                yaml.dump(providers_data, f)

            loader = ConfigLoader(data_dir)
            config = loader.load_providers_config()
            assert config.providers[0].config["api_key"] == "secret-key-123"

            del os.environ["TEST_API_KEY"]

    def test_load_app_config_from_toml(self):
        """Test loading app config from toml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)

            config_file = data_dir / "config.toml"
            config_file.write_text(
                'server = { host = "localhost", port = 4321 }\n',
                encoding="utf-8",
            )

            loader = ConfigLoader(data_dir)
            config = loader.load_app_config()
            assert config.server.host == "localhost"
            assert config.server.port == 4321

    def test_load_providers_config_from_toml(self):
        """Test loading providers config from toml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = _prepare_data_dir(tmpdir)

            providers_file = data_dir / "providers.toml"
            providers_file.write_text(
                'default = "openai-1"\n'
                "\n"
                "[[providers]]\n"
                'id = "openai-1"\n'
                'type = "openai"\n'
                'name = "OpenAI"\n'
                "enabled = true\n"
                "[providers.config]\n"
                'api_key = "sk-test"\n',
                encoding="utf-8",
            )

            loader = ConfigLoader(data_dir)
            config = loader.load_providers_config()
            assert len(config.providers) == 1
            assert config.providers[0].id == "openai-1"
