"""
图像预处理工具

提供灰度处理、二值化、边缘检测、去噪、锐化等基础图像预处理功能。
"""

from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """转换为灰度图

    Args:
        image: BGR 或灰度图像

    Returns:
        灰度图像
    """
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def to_binary(
    image: np.ndarray,
    threshold: int = 127,
    max_value: int = 255,
    method: int = cv2.THRESH_BINARY,
) -> np.ndarray:
    """二值化处理

    Args:
        image: 输入图像
        threshold: 阈值
        max_value: 最大值
        method: 二值化方法

    Returns:
        二值化图像
    """
    gray = to_grayscale(image)
    _, binary = cv2.threshold(gray, threshold, max_value, method)
    return binary


def adaptive_threshold(
    image: np.ndarray,
    max_value: int = 255,
    method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    threshold_type: int = cv2.THRESH_BINARY,
    block_size: int = 11,
    c: int = 2,
) -> np.ndarray:
    """自适应阈值二值化

    Args:
        image: 输入图像
        max_value: 最大值
        method: 自适应方法
        threshold_type: 阈值类型
        block_size: 块大小
        c: 常数

    Returns:
        二值化图像
    """
    gray = to_grayscale(image)
    return cv2.adaptiveThreshold(gray, max_value, method, threshold_type, block_size, c)


def otsu_threshold(image: np.ndarray, max_value: int = 255) -> np.ndarray:
    """Otsu 自动阈值二值化

    Args:
        image: 输入图像
        max_value: 最大值

    Returns:
        二值化图像
    """
    gray = to_grayscale(image)
    _, binary = cv2.threshold(gray, 0, max_value, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def edge_detection(
    image: np.ndarray,
    low_threshold: int = 50,
    high_threshold: int = 150,
) -> np.ndarray:
    """Canny 边缘检测

    Args:
        image: 输入图像
        low_threshold: 低阈值
        high_threshold: 高阈值

    Returns:
        边缘图像
    """
    gray = to_grayscale(image)
    return cv2.Canny(gray, low_threshold, high_threshold)


def denoise(
    image: np.ndarray,
    h: float = 10.0,
    template_window_size: int = 7,
    search_window_size: int = 21,
) -> np.ndarray:
    """去噪处理

    Args:
        image: 输入图像
        h: 滤波强度
        template_window_size: 模板窗口大小
        search_window_size: 搜索窗口大小

    Returns:
        去噪后的图像
    """
    if len(image.shape) == 2:
        return cv2.fastNlMeansDenoising(image, None, h, template_window_size, search_window_size)
    return cv2.fastNlMeansDenoisingColored(image, None, h, h, template_window_size, search_window_size)


def sharpen(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """锐化处理

    Args:
        image: 输入图像
        strength: 锐化强度

    Returns:
        锐化后的图像
    """
    kernel = np.array(
        [
            [0, -1, 0],
            [-1, 5 + strength, -1],
            [0, -1, 0],
        ]
    )
    return cv2.filter2D(image, -1, kernel)


def blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """高斯模糊

    Args:
        image: 输入图像
        kernel_size: 核大小

    Returns:
        模糊后的图像
    """
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def resize(
    image: np.ndarray,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    interpolation: int = cv2.INTER_LINEAR,
) -> np.ndarray:
    """调整图像大小

    Args:
        image: 输入图像
        width: 目标宽度
        height: 目标高度
        scale: 缩放比例
        interpolation: 插值方法

    Returns:
        调整后的图像
    """
    h, w = image.shape[:2]

    if scale is not None:
        new_w = int(w * scale)
        new_h = int(h * scale)
    elif width is not None and height is not None:
        new_w, new_h = width, height
    elif width is not None:
        new_w = width
        new_h = int(h * width / w)
    elif height is not None:
        new_h = height
        new_w = int(w * height / h)
    else:
        return image

    return cv2.resize(image, (new_w, new_h), interpolation=interpolation)
