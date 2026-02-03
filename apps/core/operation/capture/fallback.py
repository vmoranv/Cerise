"""Capture backend that falls back across multiple methods."""

from __future__ import annotations

from collections.abc import Sequence

from .base import CaptureMethod


class FallbackCapture:
    """Try multiple capture methods in order until one works."""

    def __init__(self, methods: Sequence[CaptureMethod]) -> None:
        self._methods = list(methods)
        self._active_index: int | None = None
        self._hwnd: int = 0

    @property
    def width(self) -> int:
        active = self._active
        return active.width if active else 0

    @property
    def height(self) -> int:
        active = self._active
        return active.height if active else 0

    @property
    def hwnd(self) -> int:
        return self._hwnd

    @property
    def _active(self) -> CaptureMethod | None:
        if self._active_index is None:
            return None
        if self._active_index < 0 or self._active_index >= len(self._methods):
            return None
        return self._methods[self._active_index]

    def connect(self, hwnd: int) -> bool:
        self.close()
        self._hwnd = int(hwnd)

        for index, method in enumerate(self._methods):
            if method.connect(self._hwnd):
                self._active_index = index
                return True

        self._active_index = None
        return False

    def connected(self) -> bool:
        active = self._active
        return active is not None and active.connected()

    def get_frame(self):
        active = self._active
        if active is None:
            return None

        frame = active.get_frame()
        if frame is not None:
            return frame

        # If the active backend fails to produce a frame, try the remaining backends once.
        if not self._hwnd:
            return None

        for index, method in enumerate(self._methods):
            if index == self._active_index:
                continue
            if not method.connect(self._hwnd):
                continue
            candidate = method.get_frame()
            if candidate is None:
                method.close()
                continue
            if active is not method:
                active.close()
            self._active_index = index
            return candidate

        return None

    def close(self) -> None:
        for method in self._methods:
            try:
                method.close()
            except Exception:
                # Best-effort cleanup for optional backends.
                pass
        self._active_index = None
        self._hwnd = 0
