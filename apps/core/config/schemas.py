"""
Configuration Schemas

Pydantic models for configuration validation.
"""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Server configuration"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class AIConfig(BaseModel):
    """AI configuration"""

    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2048


class PluginsConfig(BaseModel):
    """Plugins configuration"""

    enabled: bool = True
    auto_start: bool = True
    plugins_dir: str = ""  # Empty = use default ~/.cerise/plugins


class TTSConfig(BaseModel):
    """TTS configuration"""

    enabled: bool = False
    provider: str = "local"
    character: str = "default"
    server_url: str = "http://localhost:5000"


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: str = "INFO"
    file: str = ""  # Empty = no file logging


class AppConfig(BaseModel):
    """Main application configuration"""

    server: ServerConfig = Field(default_factory=ServerConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ----- Provider Configuration -----


class ProviderConfig(BaseModel):
    """Single provider configuration"""

    id: str
    type: str  # openai, claude, gemini, ollama
    name: str = ""
    enabled: bool = True
    config: dict = Field(default_factory=dict)


class ProvidersConfig(BaseModel):
    """All providers configuration"""

    default: str = ""
    providers: list[ProviderConfig] = Field(default_factory=list)


# ----- Character Configuration -----


class PersonalityTraits(BaseModel):
    """Big Five personality traits"""

    openness: float = 0.7
    conscientiousness: float = 0.6
    extraversion: float = 0.7
    agreeableness: float = 0.8
    neuroticism: float = 0.3


class VoiceConfig(BaseModel):
    """Voice configuration"""

    enabled: bool = False
    character: str = "default"
    provider: str = "local"


class CharacterConfig(BaseModel):
    """Character configuration"""

    name: str = "Cerise"
    language: str = "zh"
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    system_prompt_template: str = ""


# ----- Plugin Installation -----


class InstalledPlugin(BaseModel):
    """Installed plugin record"""

    name: str
    version: str
    source: str  # github, local, zip
    source_url: str = ""
    enabled: bool = True
    installed_at: str = ""


class PluginsRegistry(BaseModel):
    """Registry of installed plugins"""

    plugins: list[InstalledPlugin] = Field(default_factory=list)
