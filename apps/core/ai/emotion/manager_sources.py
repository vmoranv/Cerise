"""
Config source helpers for emotion manager.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from .config_loader import load_emotion_config
from .config_models import EmotionConfig
from .config_utils import emotion_config_from_dict, merge_emotion_configs
from .manager_types import _ConfigSource, _PipelineCache

logger = logging.getLogger(__name__)


class ConfigSourceMixin:
    _config_path: Path
    _data_dir: Path
    _base_config: EmotionConfig
    _base_mtime: float
    _plugin_paths: set[Path]
    _cache: dict[str, _PipelineCache]

    def _load_base_config(self) -> None:
        if not self._config_path.exists():
            return
        mtime = self._config_path.stat().st_mtime
        if mtime <= self._base_mtime:
            return
        self._base_config = load_emotion_config(self._config_path)
        self._base_mtime = mtime
        self._cache.clear()

    def _build_profile_config(self, character: str | None) -> tuple[EmotionConfig, list[Path], list[_ConfigSource]]:
        plugin_configs, plugin_paths = self._load_plugin_configs(self._base_config)
        character_config, character_path = self._load_character_config(character)
        overrides = plugin_configs[:]
        if character_config:
            overrides.append(character_config)
        merged = merge_emotion_configs(self._base_config, overrides)
        config_chain = [
            _ConfigSource(
                config=self._base_config, source_path=self._config_path if self._config_path.exists() else None
            )
        ]
        config_chain.extend([_ConfigSource(config=cfg, source_path=path) for cfg, path in plugin_paths])
        if character_config:
            config_chain.append(_ConfigSource(config=character_config, source_path=character_path))

        sources = [source.source_path for source in config_chain if source.source_path]
        sources.extend(self._lexicon_paths_from_chain(config_chain))
        return merged, sources, config_chain

    def _load_plugin_configs(
        self, base_config: EmotionConfig
    ) -> tuple[list[EmotionConfig], list[tuple[EmotionConfig, Path]]]:
        plugin_paths = set(self._plugin_paths)
        plugins_dir = Path(base_config.plugins_dir) if base_config.plugins_dir else self._data_dir / "plugins"
        if plugins_dir.exists():
            plugin_paths.update(plugins_dir.glob(base_config.plugin_glob))
        for entry in base_config.plugins:
            path = Path(entry)
            if not path.is_absolute():
                path = (plugins_dir / path) if plugins_dir.exists() else (self._data_dir / entry)
            if path.is_dir():
                candidate = path / "emotion.yaml"
                if candidate.exists():
                    plugin_paths.add(candidate)
                else:
                    plugin_paths.update(path.glob(base_config.plugin_glob))
            elif path.exists():
                plugin_paths.add(path)

        configs: list[EmotionConfig] = []
        resolved_paths: list[tuple[EmotionConfig, Path]] = []
        for path in sorted(plugin_paths):
            if not path.exists():
                continue
            try:
                config = load_emotion_config(path)
                configs.append(config)
                resolved_paths.append((config, path))
            except Exception as exc:
                logger.warning("Failed to load emotion plugin %s: %s", path, exc)
        return configs, resolved_paths

    def _load_character_config(self, character: str | None) -> tuple[EmotionConfig | None, Path | None]:
        if not character:
            return None, None
        path = self._data_dir / "characters" / f"{character}.yaml"
        if not path.exists():
            return None, None
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            emotion_data = data.get("emotion", {}) if isinstance(data, dict) else {}
            if not emotion_data:
                return None, None
            return emotion_config_from_dict(emotion_data), path
        except Exception as exc:
            logger.warning("Failed to load character emotion config %s: %s", path, exc)
            return None, path

    def _sources_changed(self, cached: _PipelineCache, sources: list[Path]) -> bool:
        cached_paths = set(cached.sources)
        current_paths = set(sources)
        if cached_paths != current_paths:
            return True
        for path in current_paths:
            if not path.exists():
                return True
            mtime = path.stat().st_mtime
            if cached.mtimes.get(path) != mtime:
                return True
        return False
