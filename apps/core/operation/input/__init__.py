"""
输入模拟模块

提供键盘、鼠标输入模拟能力。
"""

from .api import (
    POINT,
    ClientToScreen,
    GetWindowRect,
    IsWindow,
    MapVirtualKeyW,
    PostMessageW,
    SendMessageW,
    SetCursorPos,
    get_vk,
    make_key_lparam,
    make_lparam,
)
from .base import Interaction
from .constants import (
    MK_LBUTTON,
    MK_MBUTTON,
    MK_RBUTTON,
    VK_CODES,
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
from .gamepad import Gamepad, GamepadState, NullGamepad
from .keymap import (
    KeyBinding,
    KeyMap,
    create_arrow_preset,
    create_wasd_preset,
)
from .policy import GamepadPolicy, NullGamepadPolicy
from .win32 import Win32Interaction

__all__ = [
    # Protocol
    "Interaction",
    "Gamepad",
    "GamepadPolicy",
    # Win32 Implementation
    "Win32Interaction",
    "NullGamepad",
    "NullGamepadPolicy",
    # Gamepad state
    "GamepadState",
    # KeyMap
    "KeyBinding",
    "KeyMap",
    "create_arrow_preset",
    "create_wasd_preset",
    # Constants
    "VK_CODES",
    "WM_MOUSEMOVE",
    "WM_LBUTTONDOWN",
    "WM_LBUTTONUP",
    "WM_LBUTTONDBLCLK",
    "WM_RBUTTONDOWN",
    "WM_RBUTTONUP",
    "WM_RBUTTONDBLCLK",
    "WM_MBUTTONDOWN",
    "WM_MBUTTONUP",
    "WM_MBUTTONDBLCLK",
    "WM_MOUSEWHEEL",
    "WM_KEYDOWN",
    "WM_KEYUP",
    "WM_CHAR",
    "MK_LBUTTON",
    "MK_RBUTTON",
    "MK_MBUTTON",
    # API helpers
    "POINT",
    "PostMessageW",
    "SendMessageW",
    "IsWindow",
    "MapVirtualKeyW",
    "GetWindowRect",
    "SetCursorPos",
    "ClientToScreen",
    "make_lparam",
    "get_vk",
    "make_key_lparam",
]
