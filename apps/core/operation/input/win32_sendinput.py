"""Win32 foreground input via SendInput.

This backend sends real input events to the OS. It is generally more reliable
for games that ignore window messages, but it usually requires the target window
to be in the foreground.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import TYPE_CHECKING

from .api import POINT, ClientToScreen, IsWindow, SetCursorPos, get_vk

if TYPE_CHECKING:
    from ..vision.box import Box


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800


ULONG_PTR = getattr(
    wintypes, "ULONG_PTR", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]


SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT


def _send_inputs(inputs: list[INPUT]) -> None:
    if not inputs:
        return
    array_type = INPUT * len(inputs)
    SendInput(len(inputs), array_type(*inputs), ctypes.sizeof(INPUT))


class Win32SendInputInteraction:
    """Foreground input backend based on SendInput + SetCursorPos."""

    def __init__(self) -> None:
        self._hwnd: int = 0
        self._connected = False
        self._last_x = 0
        self._last_y = 0

    @property
    def hwnd(self) -> int:
        return self._hwnd

    def connect(self, hwnd: int) -> bool:
        hwnd = int(hwnd)
        if not IsWindow(hwnd):
            return False
        self._hwnd = hwnd
        self._connected = True
        return True

    def connected(self) -> bool:
        return self._connected and self._hwnd != 0 and IsWindow(self._hwnd)

    def _client_to_screen(self, x: int, y: int) -> tuple[int, int]:
        point = POINT(int(x), int(y))
        ClientToScreen(self._hwnd, ctypes.byref(point))
        return int(point.x), int(point.y)

    # ========== Mouse ==========

    def move(self, x: int, y: int) -> None:
        if not self.connected():
            return
        self._last_x = int(x)
        self._last_y = int(y)
        screen_x, screen_y = self._client_to_screen(self._last_x, self._last_y)
        SetCursorPos(screen_x, screen_y)

    def _mouse_button(self, *, down: bool, button: str) -> None:
        if button == "left":
            flag = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
        elif button == "right":
            flag = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            flag = MOUSEEVENTF_MIDDLEDOWN if down else MOUSEEVENTF_MIDDLEUP
        else:
            return
        _send_inputs([INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, flag, 0, 0))])

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        if x is None:
            x = self._last_x
        if y is None:
            y = self._last_y
        self.move(x, y)
        self.mouse_down(x, y, button)
        time.sleep(0.01)
        self.mouse_up(x, y, button)

    def double_click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        self.click(x, y, button)
        time.sleep(0.05)
        self.click(x, y, button)

    def click_box(self, box: Box, button: str = "left", relative_x: float = 0.5, relative_y: float = 0.5) -> None:
        x = int(box.x + box.width * relative_x)
        y = int(box.y + box.height * relative_y)
        self.click(x, y, button)

    def mouse_down(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        if x is not None and y is not None:
            self.move(x, y)
        if not self.connected():
            return
        self._mouse_button(down=True, button=button)

    def mouse_up(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        if x is not None and y is not None:
            self.move(x, y)
        if not self.connected():
            return
        self._mouse_button(down=False, button=button)

    def scroll(self, x: int, y: int, delta: int) -> None:
        if not self.connected():
            return
        self.move(x, y)
        wheel_delta = int(delta) * 120
        _send_inputs([INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, wheel_delta, MOUSEEVENTF_WHEEL, 0, 0))])

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        button: str = "left",
        duration: float = 0.0,
    ) -> None:
        self.move(from_x, from_y)
        self.mouse_down(from_x, from_y, button)

        if duration > 0:
            steps = max(1, int(duration * 60))
            dx = (to_x - from_x) / steps
            dy = (to_y - from_y) / steps
            sleep_time = duration / steps
            for i in range(1, steps + 1):
                x = int(from_x + dx * i)
                y = int(from_y + dy * i)
                self.move(x, y)
                time.sleep(sleep_time)
        else:
            self.move(to_x, to_y)

        self.mouse_up(to_x, to_y, button)

    # ========== Keyboard ==========

    def _key_event(self, vk: int, *, down: bool) -> None:
        flags = 0 if down else KEYEVENTF_KEYUP
        _send_inputs([INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0))])

    def key_down(self, key: str) -> None:
        vk = get_vk(key)
        if vk == 0:
            return
        self._key_event(vk, down=True)

    def key_up(self, key: str) -> None:
        vk = get_vk(key)
        if vk == 0:
            return
        self._key_event(vk, down=False)

    def key_press(self, key: str, duration: float = 0.0) -> None:
        self.key_down(key)
        time.sleep(duration if duration > 0 else 0.01)
        self.key_up(key)

    def type_text(self, text: str, interval: float = 0.0) -> None:
        for char in text:
            codepoint = ord(char)
            down = INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(wVk=0, wScan=codepoint, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0),
            )
            up = INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(
                    wVk=0, wScan=codepoint, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0
                ),
            )
            _send_inputs([down, up])
            if interval > 0:
                time.sleep(interval)

    def hotkey(self, *keys: str) -> None:
        for key in keys:
            self.key_down(key)
            time.sleep(0.01)
        for key in reversed(keys):
            self.key_up(key)
            time.sleep(0.01)

    def close(self) -> None:
        self._connected = False
        self._hwnd = 0
