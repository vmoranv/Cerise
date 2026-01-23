"""Proactive chat configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...config.file_utils import load_config_data, resolve_config_path
from ...config.loader import get_data_dir

DEFAULT_PROMPT = (
    "[System Task: Proactive Chat]\n"
    "You are initiating a proactive message to the user.\n"
    "Current time: {{current_time}}.\n"
    "Unanswered count: {{unanswered_count}}.\n"
    "Review recent context and send a short, natural opener."
)


@dataclass
class ProactiveScheduleConfig:
    """Scheduling rules for proactive chat."""

    min_interval_minutes: int = 30
    max_interval_minutes: int = 900
    quiet_hours: str = "1-7"
    max_unanswered_times: int = 4


@dataclass
class ProactiveAutoTriggerConfig:
    """Auto trigger settings for proactive chat."""

    enabled: bool = False
    after_minutes: int = 5


@dataclass
class ProactiveSessionConfig:
    """Per-session proactive chat configuration."""

    session_id: str
    enabled: bool = True
    prompt: str = DEFAULT_PROMPT
    provider_id: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 512
    schedule: ProactiveScheduleConfig = field(default_factory=ProactiveScheduleConfig)
    auto_trigger: ProactiveAutoTriggerConfig = field(default_factory=ProactiveAutoTriggerConfig)


@dataclass
class ProactiveChatConfig:
    """Top-level proactive chat configuration."""

    enabled: bool = False
    state_path: str = ""
    timezone: str = ""
    apply_to_all_sessions: bool = False
    session_allowlist: list[str] = field(default_factory=list)
    prompt: str = DEFAULT_PROMPT
    provider_id: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 512
    schedule: ProactiveScheduleConfig = field(default_factory=ProactiveScheduleConfig)
    auto_trigger: ProactiveAutoTriggerConfig = field(default_factory=ProactiveAutoTriggerConfig)
    sessions: list[ProactiveSessionConfig] = field(default_factory=list)


def _merge_dict(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _session_from_dict(data: dict[str, Any], defaults: ProactiveChatConfig) -> ProactiveSessionConfig | None:
    session_id = data.get("session_id") or data.get("id")
    if not session_id:
        return None
    schedule_data = _merge_dict(defaults.schedule.__dict__, data.get("schedule", {}) or {})
    auto_data = _merge_dict(defaults.auto_trigger.__dict__, data.get("auto_trigger", {}) or {})

    return ProactiveSessionConfig(
        session_id=str(session_id),
        enabled=bool(data.get("enabled", True)),
        prompt=str(data.get("prompt") or defaults.prompt),
        provider_id=str(data.get("provider_id") or defaults.provider_id),
        model=str(data.get("model") or defaults.model),
        temperature=float(data.get("temperature", defaults.temperature)),
        max_tokens=int(data.get("max_tokens", defaults.max_tokens)),
        schedule=ProactiveScheduleConfig(**schedule_data),
        auto_trigger=ProactiveAutoTriggerConfig(**auto_data),
    )


def load_proactive_config(path: str | Path | None = None) -> ProactiveChatConfig:
    """Load proactive chat configuration from yaml or toml."""
    if path is None:
        path = Path(get_data_dir()) / "proactive.yaml"
    path = resolve_config_path(Path(path))

    defaults = ProactiveChatConfig()
    data: dict[str, Any] = load_config_data(path)
    merged = _merge_dict(defaults_to_dict(defaults), data)

    sessions: list[ProactiveSessionConfig] = []
    for item in merged.get("sessions", []) or []:
        if isinstance(item, dict):
            session = _session_from_dict(item, defaults)
            if session:
                sessions.append(session)

    config = ProactiveChatConfig(
        enabled=bool(merged.get("enabled", defaults.enabled)),
        state_path=str(merged.get("state_path") or ""),
        timezone=str(merged.get("timezone") or ""),
        apply_to_all_sessions=bool(merged.get("apply_to_all_sessions", defaults.apply_to_all_sessions)),
        session_allowlist=list(merged.get("session_allowlist", defaults.session_allowlist) or []),
        prompt=str(merged.get("prompt") or defaults.prompt),
        provider_id=str(merged.get("provider_id") or defaults.provider_id),
        model=str(merged.get("model") or defaults.model),
        temperature=float(merged.get("temperature", defaults.temperature)),
        max_tokens=int(merged.get("max_tokens", defaults.max_tokens)),
        schedule=ProactiveScheduleConfig(**merged.get("schedule", {})),
        auto_trigger=ProactiveAutoTriggerConfig(**merged.get("auto_trigger", {})),
        sessions=sessions,
    )

    if not config.state_path:
        config.state_path = str(Path(get_data_dir()) / "proactive" / "state.json")

    return config


def defaults_to_dict(config: ProactiveChatConfig) -> dict[str, Any]:
    return {
        "enabled": config.enabled,
        "state_path": config.state_path,
        "timezone": config.timezone,
        "apply_to_all_sessions": config.apply_to_all_sessions,
        "session_allowlist": list(config.session_allowlist),
        "prompt": config.prompt,
        "provider_id": config.provider_id,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "schedule": config.schedule.__dict__,
        "auto_trigger": config.auto_trigger.__dict__,
        "sessions": [session.__dict__ for session in config.sessions],
    }
