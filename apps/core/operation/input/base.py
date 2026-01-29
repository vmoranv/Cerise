"""
输入模拟协议接口

定义统一的输入模拟接口，支持多种输入后端实现。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..vision.box import Box


@runtime_checkable
class Interaction(Protocol):
    """输入模拟协议

    所有输入后端实现必须符合此协议接口。
    支持的后端包括：
    - Win32 PostMessage (后台输入)
    - DirectInput (游戏输入)
    - pydirectinput (前台输入)
    """

    @property
    def hwnd(self) -> int:
        """当前绑定的窗口句柄"""
        ...

    def connect(self, hwnd: int) -> bool:
        """连接到目标窗口

        Args:
            hwnd: 目标窗口句柄

        Returns:
            连接是否成功
        """
        ...

    def connected(self) -> bool:
        """检查是否已连接到窗口"""
        ...

    # ========== 鼠标操作 ==========

    def move(self, x: int, y: int) -> None:
        """移动鼠标到指定位置

        Args:
            x: 目标 x 坐标（相对于窗口客户区）
            y: 目标 y 坐标（相对于窗口客户区）
        """
        ...

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
    ) -> None:
        """点击鼠标

        Args:
            x: 点击位置 x 坐标，None 表示当前位置
            y: 点击位置 y 坐标，None 表示当前位置
            button: 鼠标按键 ('left', 'right', 'middle')
        """
        ...

    def double_click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
    ) -> None:
        """双击鼠标"""
        ...

    def click_box(
        self,
        box: Box,
        button: str = "left",
        relative_x: float = 0.5,
        relative_y: float = 0.5,
    ) -> None:
        """点击 Box 区域

        Args:
            box: 目标区域
            button: 鼠标按键
            relative_x: 相对于 Box 宽度的点击位置 (0.0-1.0)
            relative_y: 相对于 Box 高度的点击位置 (0.0-1.0)
        """
        ...

    def mouse_down(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """按下鼠标按键"""
        ...

    def mouse_up(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """释放鼠标按键"""
        ...

    def scroll(self, x: int, y: int, delta: int) -> None:
        """滚动鼠标滚轮

        Args:
            x: 滚动位置 x 坐标
            y: 滚动位置 y 坐标
            delta: 滚动量（正值向上，负值向下）
        """
        ...

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        button: str = "left",
        duration: float = 0.0,
    ) -> None:
        """拖拽操作

        Args:
            from_x: 起始 x 坐标
            from_y: 起始 y 坐标
            to_x: 目标 x 坐标
            to_y: 目标 y 坐标
            button: 鼠标按键
            duration: 拖拽持续时间（秒）
        """
        ...

    # ========== 键盘操作 ==========

    def key_down(self, key: str) -> None:
        """按下键盘按键

        Args:
            key: 按键名称（如 'a', 'enter', 'ctrl'）
        """
        ...

    def key_up(self, key: str) -> None:
        """释放键盘按键"""
        ...

    def key_press(self, key: str, duration: float = 0.0) -> None:
        """按下并释放按键

        Args:
            key: 按键名称
            duration: 按住时间（秒）
        """
        ...

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本

        Args:
            text: 要输入的文本
            interval: 按键间隔（秒）
        """
        ...

    def hotkey(self, *keys: str) -> None:
        """执行组合键

        Args:
            keys: 按键序列（如 'ctrl', 'c'）
        """
        ...

    def close(self) -> None:
        """释放资源"""
        ...
