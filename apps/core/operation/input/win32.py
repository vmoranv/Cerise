"""
Win32 输入模拟实现

使用 Windows API 进行输入模拟：
- PostMessage: 后台输入（不需要窗口在前台）
- SendInput: 前台输入（更可靠但需要窗口在前台）
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .api import (
    IsWindow,
    PostMessageW,
    SendMessageW,
    get_vk,
    make_key_lparam,
    make_lparam,
)
from .constants import (
    MK_LBUTTON,
    MK_MBUTTON,
    MK_RBUTTON,
    WM_CHAR,
    WM_KEYDOWN,
    WM_KEYUP,
    WM_LBUTTONDBLCLK,
    WM_LBUTTONDOWN,
    WM_LBUTTONUP,
    WM_MBUTTONDBLCLK,
    WM_MBUTTONDOWN,
    WM_MBUTTONUP,
    WM_MOUSEMOVE,
    WM_MOUSEWHEEL,
    WM_RBUTTONDBLCLK,
    WM_RBUTTONDOWN,
    WM_RBUTTONUP,
)

if TYPE_CHECKING:
    from ..vision.box import Box


class Win32Interaction:
    """Win32 输入模拟

    使用 PostMessage 实现后台输入模拟。
    适用于大多数普通应用程序，不需要窗口在前台。

    Example:
        >>> interaction = Win32Interaction()
        >>> interaction.connect(hwnd)
        >>> interaction.click(100, 200)
        >>> interaction.key_press('enter')
        >>> interaction.close()
    """

    def __init__(self, use_send_message: bool = False) -> None:
        """初始化输入模拟器

        Args:
            use_send_message: 是否使用 SendMessage（同步）而非 PostMessage（异步）
        """
        self._hwnd: int = 0
        self._use_send_message = use_send_message
        self._last_x: int = 0
        self._last_y: int = 0

    @property
    def hwnd(self) -> int:
        return self._hwnd

    def connect(self, hwnd: int) -> bool:
        """连接到目标窗口"""
        if not IsWindow(hwnd):
            return False
        self._hwnd = hwnd
        return True

    def connected(self) -> bool:
        """检查是否已连接"""
        return self._hwnd != 0 and IsWindow(self._hwnd)

    def _send(self, msg: int, wparam: int, lparam: int) -> None:
        """发送消息到窗口"""
        if not self.connected():
            return
        if self._use_send_message:
            SendMessageW(self._hwnd, msg, wparam, lparam)
        else:
            PostMessageW(self._hwnd, msg, wparam, lparam)

    # ========== 鼠标操作 ==========

    def move(self, x: int, y: int) -> None:
        """移动鼠标"""
        self._last_x = x
        self._last_y = y
        lparam = make_lparam(x, y)
        self._send(WM_MOUSEMOVE, 0, lparam)

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
    ) -> None:
        """点击鼠标"""
        if x is None:
            x = self._last_x
        if y is None:
            y = self._last_y

        self.move(x, y)
        self.mouse_down(x, y, button)
        time.sleep(0.01)
        self.mouse_up(x, y, button)

    def double_click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
    ) -> None:
        """双击鼠标"""
        if x is None:
            x = self._last_x
        if y is None:
            y = self._last_y

        lparam = make_lparam(x, y)
        self.move(x, y)

        if button == "left":
            self._send(WM_LBUTTONDBLCLK, MK_LBUTTON, lparam)
        elif button == "right":
            self._send(WM_RBUTTONDBLCLK, MK_RBUTTON, lparam)
        elif button == "middle":
            self._send(WM_MBUTTONDBLCLK, MK_MBUTTON, lparam)

    def click_box(
        self,
        box: Box,
        button: str = "left",
        relative_x: float = 0.5,
        relative_y: float = 0.5,
    ) -> None:
        """点击 Box 区域"""
        x = int(box.x + box.width * relative_x)
        y = int(box.y + box.height * relative_y)
        self.click(x, y, button)

    def mouse_down(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """按下鼠标"""
        if x is None:
            x = self._last_x
        if y is None:
            y = self._last_y

        lparam = make_lparam(x, y)

        if button == "left":
            self._send(WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        elif button == "right":
            self._send(WM_RBUTTONDOWN, MK_RBUTTON, lparam)
        elif button == "middle":
            self._send(WM_MBUTTONDOWN, MK_MBUTTON, lparam)

    def mouse_up(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """释放鼠标"""
        if x is None:
            x = self._last_x
        if y is None:
            y = self._last_y

        lparam = make_lparam(x, y)

        if button == "left":
            self._send(WM_LBUTTONUP, 0, lparam)
        elif button == "right":
            self._send(WM_RBUTTONUP, 0, lparam)
        elif button == "middle":
            self._send(WM_MBUTTONUP, 0, lparam)

    def scroll(self, x: int, y: int, delta: int) -> None:
        """滚动鼠标滚轮"""
        self.move(x, y)
        wparam = (delta * 120) << 16
        lparam = make_lparam(x, y)
        self._send(WM_MOUSEWHEEL, wparam, lparam)

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        button: str = "left",
        duration: float = 0.0,
    ) -> None:
        """拖拽操作"""
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

    # ========== 键盘操作 ==========

    def key_down(self, key: str) -> None:
        """按下键盘按键"""
        vk = get_vk(key)
        if vk == 0:
            return
        lparam = make_key_lparam(vk, down=True)
        self._send(WM_KEYDOWN, vk, lparam)

    def key_up(self, key: str) -> None:
        """释放键盘按键"""
        vk = get_vk(key)
        if vk == 0:
            return
        lparam = make_key_lparam(vk, down=False)
        self._send(WM_KEYUP, vk, lparam)

    def key_press(self, key: str, duration: float = 0.0) -> None:
        """按下并释放按键"""
        self.key_down(key)
        if duration > 0:
            time.sleep(duration)
        else:
            time.sleep(0.01)
        self.key_up(key)

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        for char in text:
            self._send(WM_CHAR, ord(char), 0)
            if interval > 0:
                time.sleep(interval)

    def hotkey(self, *keys: str) -> None:
        """执行组合键"""
        for key in keys:
            self.key_down(key)
            time.sleep(0.01)

        for key in reversed(keys):
            self.key_up(key)
            time.sleep(0.01)

    def close(self) -> None:
        """释放资源"""
        self._hwnd = 0

    def __enter__(self) -> Win32Interaction:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
