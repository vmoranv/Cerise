"""
窗口管理器

提供 Windows 窗口查找、管理功能。
"""

from __future__ import annotations

import ctypes
import re
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from re import Pattern

# Win32 API
user32 = ctypes.windll.user32

EnumWindows = user32.EnumWindows
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClassNameW = user32.GetClassNameW
IsWindow = user32.IsWindow
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowRect = user32.GetWindowRect
GetClientRect = user32.GetClientRect
SetForegroundWindow = user32.SetForegroundWindow
ShowWindow = user32.ShowWindow
GetForegroundWindow = user32.GetForegroundWindow

# 回调函数类型
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

# ShowWindow 常量
SW_RESTORE = 9
SW_SHOW = 5
SW_MINIMIZE = 6


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


@dataclass
class WindowInfo:
    """窗口信息"""

    hwnd: int
    title: str
    class_name: str
    pid: int
    x: int
    y: int
    width: int
    height: int
    client_width: int
    client_height: int
    visible: bool

    def __repr__(self) -> str:
        return (
            f"WindowInfo(hwnd={self.hwnd}, title='{self.title}', "
            f"class='{self.class_name}', size={self.width}x{self.height})"
        )


def get_window_title(hwnd: int) -> str:
    """获取窗口标题"""
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_window_class(hwnd: int) -> str:
    """获取窗口类名"""
    buffer = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def get_window_pid(hwnd: int) -> int:
    """获取窗口进程 ID"""
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """获取窗口矩形 (left, top, right, bottom)"""
    rect = RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def get_client_rect(hwnd: int) -> tuple[int, int]:
    """获取客户区大小 (width, height)"""
    rect = RECT()
    GetClientRect(hwnd, ctypes.byref(rect))
    return rect.right - rect.left, rect.bottom - rect.top


def get_window_info(hwnd: int) -> WindowInfo | None:
    """获取窗口详细信息"""
    if not IsWindow(hwnd):
        return None

    title = get_window_title(hwnd)
    class_name = get_window_class(hwnd)
    pid = get_window_pid(hwnd)
    left, top, right, bottom = get_window_rect(hwnd)
    client_width, client_height = get_client_rect(hwnd)

    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name=class_name,
        pid=pid,
        x=left,
        y=top,
        width=right - left,
        height=bottom - top,
        client_width=client_width,
        client_height=client_height,
        visible=bool(IsWindowVisible(hwnd)),
    )


def enum_windows(
    filter_func: Callable[[int], bool] | None = None,
    visible_only: bool = True,
) -> list[int]:
    """枚举所有窗口

    Args:
        filter_func: 可选的过滤函数，返回 True 表示保留
        visible_only: 是否只返回可见窗口

    Returns:
        窗口句柄列表
    """
    windows: list[int] = []

    def callback(hwnd: int, lparam: int) -> bool:
        if visible_only and not IsWindowVisible(hwnd):
            return True

        if filter_func is None or filter_func(hwnd):
            windows.append(hwnd)
        return True

    EnumWindows(WNDENUMPROC(callback), 0)
    return windows


def find_window_by_title(
    title: str | Pattern[str],
    exact: bool = False,
    visible_only: bool = True,
) -> int | None:
    """根据标题查找窗口

    Args:
        title: 窗口标题（字符串或正则表达式）
        exact: 是否精确匹配
        visible_only: 是否只搜索可见窗口

    Returns:
        窗口句柄，未找到返回 None
    """

    def match(hwnd: int) -> bool:
        window_title = get_window_title(hwnd)
        if isinstance(title, Pattern):
            return bool(re.search(title, window_title))
        elif exact:
            return window_title == title
        else:
            return title in window_title

    windows = enum_windows(match, visible_only)
    return windows[0] if windows else None


def find_window_by_class(
    class_name: str | Pattern[str],
    visible_only: bool = True,
) -> int | None:
    """根据类名查找窗口

    Args:
        class_name: 窗口类名（字符串或正则表达式）
        visible_only: 是否只搜索可见窗口

    Returns:
        窗口句柄，未找到返回 None
    """

    def match(hwnd: int) -> bool:
        window_class = get_window_class(hwnd)
        if isinstance(class_name, Pattern):
            return bool(re.search(class_name, window_class))
        else:
            return window_class == class_name

    windows = enum_windows(match, visible_only)
    return windows[0] if windows else None


def find_windows(
    title: str | Pattern[str] | None = None,
    class_name: str | Pattern[str] | None = None,
    visible_only: bool = True,
) -> list[WindowInfo]:
    """查找符合条件的所有窗口

    Args:
        title: 窗口标题（可选）
        class_name: 窗口类名（可选）
        visible_only: 是否只搜索可见窗口

    Returns:
        WindowInfo 列表
    """

    def match(hwnd: int) -> bool:
        if title is not None:
            window_title = get_window_title(hwnd)
            if isinstance(title, Pattern):
                if not re.search(title, window_title):
                    return False
            elif title not in window_title:
                return False

        if class_name is not None:
            window_class = get_window_class(hwnd)
            if isinstance(class_name, Pattern):
                if not re.search(class_name, window_class):
                    return False
            elif window_class != class_name:
                return False

        return True

    windows = enum_windows(match, visible_only)
    result = []
    for hwnd in windows:
        info = get_window_info(hwnd)
        if info:
            result.append(info)
    return result


def bring_to_front(hwnd: int) -> bool:
    """将窗口置于前台

    Args:
        hwnd: 窗口句柄

    Returns:
        是否成功
    """
    if not IsWindow(hwnd):
        return False

    # 如果窗口最小化，先恢复
    ShowWindow(hwnd, SW_RESTORE)
    return bool(SetForegroundWindow(hwnd))


def is_foreground(hwnd: int) -> bool:
    """检查窗口是否在前台"""
    return GetForegroundWindow() == hwnd


def minimize_window(hwnd: int) -> bool:
    """最小化窗口"""
    if not IsWindow(hwnd):
        return False
    return bool(ShowWindow(hwnd, SW_MINIMIZE))


def restore_window(hwnd: int) -> bool:
    """恢复窗口"""
    if not IsWindow(hwnd):
        return False
    return bool(ShowWindow(hwnd, SW_RESTORE))
