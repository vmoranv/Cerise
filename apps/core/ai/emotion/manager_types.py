"""
Types for emotion config manager.
"""

from dataclasses import dataclass
from pathlib import Path

from .config_models import EmotionConfig
from .pipeline import EmotionPipeline


@dataclass
class _PipelineCache:
    pipeline: EmotionPipeline
    sources: list[Path]
    mtimes: dict[Path, float]


@dataclass
class _ConfigSource:
    config: EmotionConfig
    source_path: Path | None
