"""
Emotion configuration merge helpers.
"""

from __future__ import annotations

from .config_models import EmotionConfig, EmotionLexiconConfig, EmotionRulesConfig


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
