"""
Emotion configuration and loaders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ...config.loader import get_data_dir


@dataclass
class EmotionLexiconConfig:
    """Lexicon config from yaml."""

    path: str = ""
    keywords: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    intensifiers: list[str] = field(default_factory=list)
    diminishers: list[str] = field(default_factory=list)
    negations: list[str] = field(default_factory=list)
    positive_hints: list[str] = field(default_factory=list)
    negative_hints: list[str] = field(default_factory=list)


@dataclass
class EmotionRuleConfig:
    """Custom rule config."""

    name: str
    emotion: str
    weight: float = 0.6
    patterns: list[str] = field(default_factory=list)
    kind: str = "regex"  # regex | contains
    priority: int = 50


@dataclass
class EmotionRulesConfig:
    """Rules configuration."""

    enabled: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)
    custom: list[EmotionRuleConfig] = field(default_factory=list)


@dataclass
class EmotionConfig:
    """Overall emotion configuration."""

    lexicon: EmotionLexiconConfig = field(default_factory=EmotionLexiconConfig)
    rules: EmotionRulesConfig = field(default_factory=EmotionRulesConfig)
    plugins_dir: str = ""
    plugin_glob: str = "**/emotion/*.yaml"
    plugins: list[str] = field(default_factory=list)


def load_emotion_config(path: str | Path | None = None) -> EmotionConfig:
    """Load emotion config from yaml."""
    if path is None:
        path = Path(get_data_dir()) / "emotion.yaml"
    path = Path(path)
    data: dict[str, Any] = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    return emotion_config_from_dict(data)


def emotion_config_from_dict(data: dict[str, Any]) -> EmotionConfig:
    lexicon_data = data.get("lexicon", {}) if isinstance(data, dict) else {}
    rules_data = data.get("rules", {}) if isinstance(data, dict) else {}

    lexicon = lexicon_config_from_dict(lexicon_data)

    custom_rules = []
    for entry in rules_data.get("custom", []) if isinstance(rules_data, dict) else []:
        if not isinstance(entry, dict):
            continue
        custom_rules.append(
            EmotionRuleConfig(
                name=str(entry.get("name", "custom")),
                emotion=str(entry.get("emotion", "neutral")),
                weight=float(entry.get("weight", 0.6)),
                patterns=_parse_list(entry.get("patterns", [])),
                kind=str(entry.get("kind", "regex")),
                priority=int(entry.get("priority", 50)),
            )
        )

    rules = EmotionRulesConfig(
        enabled=_parse_list(rules_data.get("enabled", [])) if isinstance(rules_data, dict) else [],
        disabled=_parse_list(rules_data.get("disabled", [])) if isinstance(rules_data, dict) else [],
        custom=custom_rules,
    )

    return EmotionConfig(
        lexicon=lexicon,
        rules=rules,
        plugins_dir=str(data.get("plugins_dir", "")) if isinstance(data, dict) else "",
        plugin_glob=str(data.get("plugin_glob", "**/emotion/*.yaml"))
        if isinstance(data, dict)
        else "**/emotion/*.yaml",
        plugins=_parse_list(data.get("plugins", [])) if isinstance(data, dict) else [],
    )


def emotion_defaults_to_dict(config: EmotionConfig) -> dict[str, Any]:
    return {
        "lexicon": _lexicon_to_dict(config.lexicon),
        "rules": _rules_to_dict(config.rules),
        "plugins_dir": config.plugins_dir,
        "plugin_glob": config.plugin_glob,
        "plugins": list(config.plugins),
    }


def lexicon_config_from_dict(data: dict[str, Any]) -> EmotionLexiconConfig:
    if not isinstance(data, dict):
        data = {}
    return EmotionLexiconConfig(
        path=str(data.get("path", "")) if data else "",
        keywords=_parse_keywords(data.get("keywords", {})),
        intensifiers=_parse_list(data.get("intensifiers", [])),
        diminishers=_parse_list(data.get("diminishers", [])),
        negations=_parse_list(data.get("negations", [])),
        positive_hints=_parse_list(data.get("positive_hints", [])),
        negative_hints=_parse_list(data.get("negative_hints", [])),
    )


def merge_emotion_configs(base: EmotionConfig, overrides: list[EmotionConfig]) -> EmotionConfig:
    merged = EmotionConfig(
        lexicon=_merge_lexicon_configs(base.lexicon, []),
        rules=_merge_rules_configs(base.rules, []),
        plugins_dir=base.plugins_dir,
        plugin_glob=base.plugin_glob,
        plugins=list(base.plugins),
    )
    configs = [base, *overrides]
    merged.lexicon = _merge_lexicon_configs(configs[0].lexicon, [cfg.lexicon for cfg in configs[1:]])
    merged.rules = _merge_rules_configs(configs[0].rules, [cfg.rules for cfg in configs[1:]])

    for cfg in overrides:
        if cfg.plugins_dir:
            merged.plugins_dir = cfg.plugins_dir
        if cfg.plugin_glob:
            merged.plugin_glob = cfg.plugin_glob
        if cfg.plugins:
            merged.plugins = _merge_list(merged.plugins, cfg.plugins)

    return merged


def _parse_keywords(raw: Any) -> dict[str, list[tuple[str, float]]]:
    if not isinstance(raw, dict):
        return {}
    parsed: dict[str, list[tuple[str, float]]] = {}
    for emotion, items in raw.items():
        entries: list[tuple[str, float]] = []
        for item in items or []:
            if isinstance(item, str):
                entries.append((item, 1.0))
            elif isinstance(item, (list, tuple)) and len(item) >= 1:
                keyword = str(item[0])
                weight = float(item[1]) if len(item) > 1 else 1.0
                entries.append((keyword, weight))
            elif isinstance(item, dict):
                for keyword, weight in item.items():
                    entries.append((str(keyword), float(weight)))
        parsed[str(emotion)] = entries
    return parsed


def _parse_list(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if item]
    return [str(raw)]


def _merge_list(base: list[str], additions: list[str]) -> list[str]:
    seen = set(base)
    merged = list(base)
    for item in additions:
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _merge_lexicon_configs(base: EmotionLexiconConfig, overrides: list[EmotionLexiconConfig]) -> EmotionLexiconConfig:
    merged = EmotionLexiconConfig(
        path=base.path,
        keywords={k: list(v) for k, v in base.keywords.items()},
        intensifiers=list(base.intensifiers),
        diminishers=list(base.diminishers),
        negations=list(base.negations),
        positive_hints=list(base.positive_hints),
        negative_hints=list(base.negative_hints),
    )
    for cfg in overrides:
        if cfg.path:
            merged.path = cfg.path
        if cfg.keywords:
            merged.keywords = _merge_keywords(merged.keywords, cfg.keywords)
        merged.intensifiers = _merge_list(merged.intensifiers, cfg.intensifiers)
        merged.diminishers = _merge_list(merged.diminishers, cfg.diminishers)
        merged.negations = _merge_list(merged.negations, cfg.negations)
        merged.positive_hints = _merge_list(merged.positive_hints, cfg.positive_hints)
        merged.negative_hints = _merge_list(merged.negative_hints, cfg.negative_hints)
    return merged


def _merge_keywords(
    base: dict[str, list[tuple[str, float]]],
    additions: dict[str, list[tuple[str, float]]],
) -> dict[str, list[tuple[str, float]]]:
    merged = {emotion: list(entries) for emotion, entries in base.items()}
    for emotion, entries in additions.items():
        existing = {keyword.lower(): (keyword, weight) for keyword, weight in merged.get(emotion, [])}
        for keyword, weight in entries:
            existing[keyword.lower()] = (keyword, weight)
        merged[emotion] = list(existing.values())
    return merged


def _merge_rules_configs(base: EmotionRulesConfig, overrides: list[EmotionRulesConfig]) -> EmotionRulesConfig:
    merged = EmotionRulesConfig(
        enabled=list(base.enabled),
        disabled=list(base.disabled),
        custom=list(base.custom),
    )
    for cfg in overrides:
        if cfg.enabled:
            merged.enabled = _merge_list(merged.enabled, cfg.enabled)
        if cfg.disabled:
            merged.disabled = _merge_list(merged.disabled, cfg.disabled)
        if cfg.custom:
            merged.custom.extend(cfg.custom)
    return merged


def _lexicon_to_dict(config: EmotionLexiconConfig) -> dict[str, Any]:
    return {
        "path": config.path,
        "keywords": config.keywords,
        "intensifiers": list(config.intensifiers),
        "diminishers": list(config.diminishers),
        "negations": list(config.negations),
        "positive_hints": list(config.positive_hints),
        "negative_hints": list(config.negative_hints),
    }


def _rules_to_dict(config: EmotionRulesConfig) -> dict[str, Any]:
    return {
        "enabled": list(config.enabled),
        "disabled": list(config.disabled),
        "custom": [
            {
                "name": rule.name,
                "emotion": rule.emotion,
                "weight": rule.weight,
                "patterns": list(rule.patterns),
                "kind": rule.kind,
                "priority": rule.priority,
            }
            for rule in config.custom
        ],
    }
