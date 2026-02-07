"""Admin API models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GitHubInstallRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class ProviderCreateRequest(BaseModel):
    id: str
    type: str
    name: str = ""
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateRequest(BaseModel):
    config: dict[str, Any]


class MemoryConfigUpdateRequest(BaseModel):
    config: dict[str, Any]


class PluginConfigUpdate(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class AbilityExecuteRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None


class StarEntryUpdate(BaseModel):
    enabled: bool | None = None
    allow_tools: bool | None = None


class StarAbilityUpdate(BaseModel):
    enabled: bool | None = None
    allow_tools: bool | None = None


class StarConfigUpdate(BaseModel):
    config: dict[str, Any]


class StarConfigValidate(BaseModel):
    config: dict[str, Any] | None = None
