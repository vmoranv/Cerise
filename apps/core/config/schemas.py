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
    top_p: float = 1.0
    max_tokens: int = 2048


class PluginsConfig(BaseModel):
    """Plugins configuration"""

    enabled: bool = True
    auto_start: bool = True
    plugins_dir: str = ""  # Empty = use default ~/.cerise/plugins
    auto_install_dependencies: bool = False
    python_venv_dir: str = ".venv"


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


class BusConfig(BaseModel):
    """Event bus configuration."""

    mode: str = "local"  # local | multiprocess
    broker_host: str = "127.0.0.1"
    broker_port: int = 8765
    auth_key: str = "cerise"
    start_broker: bool = True


class CapabilityToggle(BaseModel):
    """Per-ability capability toggle."""

    enabled: bool = True
    allow_tools: bool = True
    priority: int = 0


class CapabilitiesConfig(BaseModel):
    """Capability scheduling configuration."""

    default_enabled: bool = True
    allow_tools_by_default: bool = True
    capabilities: dict[str, CapabilityToggle] = Field(default_factory=dict)


class ToolCallConfig(BaseModel):
    """Tool-calling execution config (permissions + context hygiene)."""

    permissions: list[str] = Field(default_factory=list)
    max_result_chars: int = 4000


class StarAbilityToggle(BaseModel):
    """Star ability toggle."""

    enabled: bool = True
    allow_tools: bool = True


class StarEntry(BaseModel):
    """Star registry entry."""

    name: str
    enabled: bool = True
    allow_tools: bool = True
    abilities: dict[str, StarAbilityToggle] = Field(default_factory=dict)

    def get_ability(self, ability_name: str) -> StarAbilityToggle | None:
        return self.abilities.get(ability_name)


class StarRegistry(BaseModel):
    """Registry of star configs."""

    stars: list[StarEntry] = Field(default_factory=list)

    def get_star(self, name: str) -> StarEntry | None:
        for star in self.stars:
            if star.name == name:
                return star
        return None


class AppConfig(BaseModel):
    """Main application configuration"""

    server: ServerConfig = Field(default_factory=ServerConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    capabilities: CapabilitiesConfig = Field(default_factory=CapabilitiesConfig)
    tools: ToolCallConfig = Field(default_factory=ToolCallConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    bus: BusConfig = Field(default_factory=BusConfig)


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


# ----- MCP Configuration -----


class McpServerEntry(BaseModel):
    """Single MCP server configuration."""

    id: str
    enabled: bool = True
    transport: str = "stdio"  # stdio | sse | websocket | streamable_http (future)
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    tool_name_prefix: str = ""


class McpConfig(BaseModel):
    """MCP servers configuration."""

    servers: list[McpServerEntry] = Field(default_factory=list)


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
