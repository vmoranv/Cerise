"""Capture-related mixin for operation service."""

from __future__ import annotations

import numpy as np

from .capture.base import CaptureMethod
from .vision.box import Box


class OperationCaptureMixin:
    """Screen capture helpers."""

    _capture: CaptureMethod

    def get_frame(self) -> np.ndarray | None:
        """Get current frame."""
        return self._capture.get_frame()

    def get_frame_region(self, box: Box) -> np.ndarray | None:
        """Get frame region cropped by box."""
        frame = self.get_frame()
        if frame is None:
            return None
        return box.crop_frame(frame)
