"""Window-related mixin for operation service."""

from __future__ import annotations

import contextlib
from re import Pattern

from apps.core.contracts.events import OPERATION_WINDOW_CONNECTED, build_operation_window_connected

from .capture.base import CaptureMethod
from .input.base import Interaction
from .input.gamepad import Gamepad
from .window import (
    WindowInfo,
    bring_to_front,
    find_window_by_title,
    find_windows,
    get_window_info,
)


class OperationWindowMixin:
    """Window management helpers."""

    _capture: CaptureMethod
    _interaction: Interaction
    _gamepad: Gamepad
    _hwnd: int

    def _publish_event(self, event_type: str, data: dict[str, object]) -> None:
        raise NotImplementedError

    def connect(self, hwnd: int) -> bool:
        """Connect to a target window."""
        if not self._capture.connect(hwnd):
            return False
        if not self._interaction.connect(hwnd):
            self._capture.close()
            return False
        with contextlib.suppress(Exception):
            self._gamepad.connect()
        self._hwnd = hwnd
        self._publish_event(
            OPERATION_WINDOW_CONNECTED,
            build_operation_window_connected(self._hwnd, self._capture.width, self._capture.height),
        )
        return True

    def connect_by_title(
        self,
        title: str | Pattern[str],
        exact: bool = False,
    ) -> bool:
        """Connect to a window by title."""
        hwnd = find_window_by_title(title, exact=exact)
        if hwnd is None:
            return False
        return self.connect(hwnd)

    def connected(self) -> bool:
        """Check connection state."""
        return self._hwnd != 0 and self._capture.connected() and self._interaction.connected()

    def get_window_info(self) -> WindowInfo | None:
        """Get current window info."""
        if self._hwnd == 0:
            return None
        return get_window_info(self._hwnd)

    def bring_to_front(self) -> bool:
        """Bring the window to the foreground."""
        if self._hwnd == 0:
            return False
        return bring_to_front(self._hwnd)

    def list_windows(
        self,
        title: str | Pattern[str] | None = None,
        class_name: str | Pattern[str] | None = None,
    ) -> list[WindowInfo]:
        """List windows matching criteria."""
        return find_windows(title=title, class_name=class_name)
