"""
Emotion configuration manager with hot reload and per-character profiles.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ...config.file_utils import resolve_config_path
from ...config.loader import get_data_dir
from ...infrastructure import EventBus
from .config_models import EmotionConfig
from .manager_lexicon import LexiconMixin
from .manager_rules import RulesMixin
from .manager_sources import ConfigSourceMixin
from .manager_types import _ConfigSource, _PipelineCache
from .pipeline import EmotionPipeline

logger = logging.getLogger(__name__)


class EmotionConfigManager(ConfigSourceMixin, LexiconMixin, RulesMixin):
    """Load emotion configs, support plugins, and hot reload per character."""

    def __init__(self, config_path: str | Path | None = None, bus: EventBus | None = None):
        self._data_dir = Path(get_data_dir())
        base_path = Path(config_path) if config_path else self._data_dir / "emotion.yaml"
        self._config_path = resolve_config_path(base_path)
        self._bus = bus
        self._base_config = EmotionConfig()
        self._base_mtime = 0.0
        self._plugin_paths: set[Path] = set()
        self._cache: dict[str, _PipelineCache] = {}
        self._load_base_config()

    def register_plugin_path(self, path: str | Path) -> None:
        self._plugin_paths.add(Path(path))
        self._cache.clear()

    def get_pipeline(self, character: str | None = None) -> EmotionPipeline:
        profile_key = character or "default"
        self._load_base_config()
        merged_config, sources, config_chain = self._build_profile_config(character)
        cached = self._cache.get(profile_key)
        if cached and not self._sources_changed(cached, sources):
            return cached.pipeline
        pipeline = self._build_pipeline(merged_config, config_chain)
        self._cache[profile_key] = _PipelineCache(
            pipeline=pipeline,
            sources=sources,
            mtimes={path: path.stat().st_mtime for path in sources if path.exists()},
        )
        return pipeline

    def _build_pipeline(self, config: EmotionConfig, config_chain: list[_ConfigSource]) -> EmotionPipeline:
        lexicon = self._build_lexicon(config_chain)
        rules = self._build_rules(config, lexicon)
        return EmotionPipeline(rules=rules, bus=self._bus)
