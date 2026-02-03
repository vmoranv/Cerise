"""No-op input interaction backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..vision.box import Box

if TYPE_CHECKING:
    pass


class NullInteraction:
    """No-op interaction backend for non-interactive environments."""

    def __init__(self) -> None:
        self._hwnd: int = 0
        self._connected: bool = False
        self._last_x: int = 0
        self._last_y: int = 0

    @property
    def hwnd(self) -> int:
        return self._hwnd

    def connect(self, hwnd: int) -> bool:
        self._hwnd = int(hwnd)
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected

    def move(self, x: int, y: int) -> None:
        self._last_x = int(x)
        self._last_y = int(y)

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:  # noqa: ARG002
        if x is not None and y is not None:
            self.move(x, y)

    def double_click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:  # noqa: ARG002
        if x is not None and y is not None:
            self.move(x, y)

    def click_box(self, box: Box, button: str = "left", relative_x: float = 0.5, relative_y: float = 0.5) -> None:  # noqa: ARG002
        x = int(box.x + box.width * relative_x)
        y = int(box.y + box.height * relative_y)
        self.move(x, y)

    def mouse_down(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:  # noqa: ARG002
        if x is not None and y is not None:
            self.move(x, y)

    def mouse_up(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:  # noqa: ARG002
        if x is not None and y is not None:
            self.move(x, y)

    def scroll(self, x: int, y: int, delta: int) -> None:  # noqa: ARG002
        self.move(x, y)

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        button: str = "left",  # noqa: ARG002
        duration: float = 0.0,  # noqa: ARG002
    ) -> None:
        self.move(from_x, from_y)
        self.move(to_x, to_y)

    def key_down(self, key: str) -> None:  # noqa: ARG002
        return None

    def key_up(self, key: str) -> None:  # noqa: ARG002
        return None

    def key_press(self, key: str, duration: float = 0.0) -> None:  # noqa: ARG002
        return None

    def type_text(self, text: str, interval: float = 0.0) -> None:  # noqa: ARG002
        return None

    def hotkey(self, *keys: str) -> None:  # noqa: ARG002
        return None

    def close(self) -> None:
        self._connected = False
        self._hwnd = 0
