"""Admin API models."""

from __future__ import annotations

from pydantic import BaseModel


class GitHubInstallRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class ProviderCreateRequest(BaseModel):
    id: str
    type: str
    name: str = ""
    enabled: bool = True
    config: dict = {}


class ConfigUpdateRequest(BaseModel):
    config: dict


class MemoryConfigUpdateRequest(BaseModel):
    config: dict


class PluginConfigUpdate(BaseModel):
    enabled: bool | None = None
    config: dict | None = None


class AbilityExecuteRequest(BaseModel):
    params: dict = {}
    user_id: str | None = None
    session_id: str | None = None


class StarEntryUpdate(BaseModel):
    enabled: bool | None = None
    allow_tools: bool | None = None


class StarAbilityUpdate(BaseModel):
    enabled: bool | None = None
    allow_tools: bool | None = None


class StarConfigUpdate(BaseModel):
    config: dict


class StarConfigValidate(BaseModel):
    config: dict | None = None
