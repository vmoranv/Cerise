"""In-memory capture backend for tests and offline usage."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


class ImageCapture:
    """Capture backend that returns frames from a preloaded image sequence."""

    def __init__(self, images: Iterable[np.ndarray] | None = None, *, loop: bool = True) -> None:
        self._images: deque[np.ndarray] = deque(images or [])
        self._loop = bool(loop)
        self._connected = False
        self._hwnd = 0
        self._width = 0
        self._height = 0

        self._refresh_size()

    def _refresh_size(self) -> None:
        if not self._images:
            self._width = 0
            self._height = 0
            return

        first = self._images[0]
        if getattr(first, "ndim", 0) >= 2:
            self._height = int(first.shape[0])
            self._width = int(first.shape[1])

    def set_images(self, images: Iterable[np.ndarray]) -> None:
        self._images = deque(images)
        self._refresh_size()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def hwnd(self) -> int:
        return self._hwnd

    def connect(self, hwnd: int) -> bool:
        self._hwnd = int(hwnd)
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected

    def get_frame(self) -> np.ndarray | None:
        if not self._connected:
            return None
        if not self._images:
            return None

        frame = self._images.popleft()
        if self._loop:
            self._images.append(frame)
        return frame

    def close(self) -> None:
        self._connected = False
        self._hwnd = 0
