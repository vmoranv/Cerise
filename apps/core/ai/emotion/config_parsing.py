"""
Emotion configuration parsing helpers.
"""

from __future__ import annotations

from typing import Any

from .config_models import EmotionConfig, EmotionLexiconConfig, EmotionRuleConfig, EmotionRulesConfig


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
