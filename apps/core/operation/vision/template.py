"""Template matching visual analysis."""

from __future__ import annotations

from .color_detection import find_color
from .template_loader import load_template, load_template_with_mask
from .template_matcher import match_template, match_template_all, match_template_multi_scale

__all__ = [
    "find_color",
    "load_template",
    "load_template_with_mask",
    "match_template",
    "match_template_all",
    "match_template_multi_scale",
]
