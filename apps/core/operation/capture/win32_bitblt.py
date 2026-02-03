"""
Win32 BitBlt 屏幕捕获实现

使用 Windows GDI BitBlt 函数进行屏幕捕获。
优点：兼容性最好，支持大多数应用
缺点：性能不如 WGC/D3D11，不支持硬件加速应用的直接捕获
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

# Win32 API 常量
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0


# Win32 结构体
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


# Win32 API 函数
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

GetWindowRect = user32.GetWindowRect
GetClientRect = user32.GetClientRect
GetWindowDC = user32.GetWindowDC
GetDC = user32.GetDC
ReleaseDC = user32.ReleaseDC
IsWindow = user32.IsWindow
IsWindowVisible = user32.IsWindowVisible
PrintWindow = user32.PrintWindow

CreateCompatibleDC = gdi32.CreateCompatibleDC
CreateCompatibleBitmap = gdi32.CreateCompatibleBitmap
SelectObject = gdi32.SelectObject
DeleteObject = gdi32.DeleteObject
DeleteDC = gdi32.DeleteDC
BitBlt = gdi32.BitBlt
GetDIBits = gdi32.GetDIBits


class Win32BitBltCapture:
    """Win32 BitBlt 屏幕捕获

    使用 GDI BitBlt 函数捕获窗口内容。
    适用于大多数普通应用程序。

    Example:
        capture = Win32BitBltCapture()
        capture.connect(hwnd)
        frame = capture.get_frame()
        if frame is not None:
            _ = frame.shape
        capture.close()
    """

    def __init__(self, use_print_window: bool = False) -> None:
        """初始化捕获器

        Args:
            use_print_window: 是否使用 PrintWindow API（某些应用需要）
        """
        self._hwnd: int = 0
        self._width: int = 0
        self._height: int = 0
        self._use_print_window = use_print_window

        # GDI 资源
        self._hdc_window: int = 0
        self._hdc_mem: int = 0
        self._hbitmap: int = 0
        self._old_bitmap: int = 0

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
        """连接到目标窗口

        Args:
            hwnd: 窗口句柄

        Returns:
            连接是否成功
        """
        # 释放之前的资源
        self.close()

        if not IsWindow(hwnd):
            return False

        # 获取窗口客户区大小
        rect = RECT()
        if not GetClientRect(hwnd, ctypes.byref(rect)):
            return False

        self._width = rect.right - rect.left
        self._height = rect.bottom - rect.top

        if self._width <= 0 or self._height <= 0:
            return False

        # 创建 GDI 资源
        self._hdc_window = GetDC(hwnd)
        if not self._hdc_window:
            return False

        self._hdc_mem = CreateCompatibleDC(self._hdc_window)
        if not self._hdc_mem:
            ReleaseDC(hwnd, self._hdc_window)
            self._hdc_window = 0
            return False

        self._hbitmap = CreateCompatibleBitmap(self._hdc_window, self._width, self._height)
        if not self._hbitmap:
            DeleteDC(self._hdc_mem)
            ReleaseDC(hwnd, self._hdc_window)
            self._hdc_mem = 0
            self._hdc_window = 0
            return False

        self._old_bitmap = SelectObject(self._hdc_mem, self._hbitmap)
        self._hwnd = hwnd

        return True

    def connected(self) -> bool:
        """检查是否已连接"""
        return self._hwnd != 0 and IsWindow(self._hwnd)

    def get_frame(self) -> np.ndarray | None:
        """获取当前帧

        Returns:
            BGR 格式的 numpy 数组，失败返回 None
        """
        if not self.connected():
            return None

        # 检查窗口大小是否变化
        rect = RECT()
        if not GetClientRect(self._hwnd, ctypes.byref(rect)):
            return None

        current_width = rect.right - rect.left
        current_height = rect.bottom - rect.top

        # 窗口大小变化时重新连接
        if current_width != self._width or current_height != self._height:
            if not self.connect(self._hwnd):
                return None

        # 捕获窗口内容
        if self._use_print_window:
            # PrintWindow 适用于某些特殊应用
            PrintWindow(self._hwnd, self._hdc_mem, 1)  # PW_CLIENTONLY = 1
        else:
            # 标准 BitBlt
            BitBlt(
                self._hdc_mem,
                0,
                0,
                self._width,
                self._height,
                self._hdc_window,
                0,
                0,
                SRCCOPY,
            )

        # 创建位图信息
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self._width
        bmi.bmiHeader.biHeight = -self._height  # 负值表示自顶向下
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32  # BGRA
        bmi.bmiHeader.biCompression = BI_RGB

        # 分配缓冲区
        buffer = np.zeros((self._height, self._width, 4), dtype=np.uint8)

        # 获取位图数据
        result = GetDIBits(
            self._hdc_mem,
            self._hbitmap,
            0,
            self._height,
            buffer.ctypes.data,
            ctypes.byref(bmi),
            DIB_RGB_COLORS,
        )

        if result == 0:
            return None

        # 转换 BGRA -> BGR
        return buffer[:, :, :3].copy()

    def close(self) -> None:
        """释放资源"""
        if self._old_bitmap and self._hdc_mem:
            SelectObject(self._hdc_mem, self._old_bitmap)
            self._old_bitmap = 0

        if self._hbitmap:
            DeleteObject(self._hbitmap)
            self._hbitmap = 0

        if self._hdc_mem:
            DeleteDC(self._hdc_mem)
            self._hdc_mem = 0

        if self._hdc_window and self._hwnd:
            ReleaseDC(self._hwnd, self._hdc_window)
            self._hdc_window = 0

        self._hwnd = 0
        self._width = 0
        self._height = 0

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> Win32BitBltCapture:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
