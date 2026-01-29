"""Template loading helpers."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def load_template(path: str | Path) -> np.ndarray | None:
    """Load a template image."""
    path = Path(path)
    if not path.exists():
        return None

    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return template


def load_template_with_mask(
    path: str | Path,
    mask_path: str | Path | None = None,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Load a template image and optional mask."""
    path = Path(path)
    if not path.exists():
        return None, None

    template = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if template is None:
        return None, None

    mask = None

    if template.shape[2] == 4:
        mask = template[:, :, 3]
        template = template[:, :, :3]

    if mask_path is not None:
        mask_path = Path(mask_path)
        if mask_path.exists():
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

    return template, mask
