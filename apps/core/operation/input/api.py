"""
Win32 API 函数封装

提供 ctypes 定义和辅助函数。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from .constants import VK_CODES

# Win32 API 函数
user32 = ctypes.windll.user32
PostMessageW = user32.PostMessageW
SendMessageW = user32.SendMessageW
IsWindow = user32.IsWindow
MapVirtualKeyW = user32.MapVirtualKeyW
GetWindowRect = user32.GetWindowRect
SetCursorPos = user32.SetCursorPos
ClientToScreen = user32.ClientToScreen


class POINT(ctypes.Structure):
    """Windows POINT 结构"""

    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def make_lparam(x: int, y: int) -> int:
    """创建 LPARAM（低16位x，高16位y）"""
    return (y << 16) | (x & 0xFFFF)


def get_vk(key: str) -> int:
    """获取虚拟键码"""
    return VK_CODES.get(key.lower(), 0)


def make_key_lparam(vk: int, down: bool = True) -> int:
    """创建键盘消息的 LPARAM"""
    scan_code = MapVirtualKeyW(vk, 0)
    repeat_count = 1
    extended = 0
    context = 0
    previous = 0 if down else 1
    transition = 0 if down else 1

    return repeat_count | (scan_code << 16) | (extended << 24) | (context << 29) | (previous << 30) | (transition << 31)
