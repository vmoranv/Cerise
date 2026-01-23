"""
图像匹配与检测工具

提供模板匹配、形状检测、直方图比较等图像分析功能。
"""

from __future__ import annotations

import cv2
import numpy as np

from operation.vision.box import Box
from operation.vision.preprocessing import (
    denoise,
    edge_detection,
    otsu_threshold,
    to_binary,
    to_grayscale,
)


def match_grayscale(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    preprocess: bool = True,
) -> Box | None:
    """灰度模板匹配

    使用灰度图进行模板匹配，提高匹配速度和鲁棒性。

    Args:
        frame: 源图像
        template: 模板图像
        threshold: 匹配阈值
        preprocess: 是否预处理（去噪、锐化）

    Returns:
        匹配到的 Box
    """
    frame_gray = to_grayscale(frame)
    template_gray = to_grayscale(template)

    if preprocess:
        frame_gray = denoise(frame_gray, h=5)
        template_gray = denoise(template_gray, h=5)

    th, tw = template_gray.shape[:2]
    result = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    return Box(
        x=max_loc[0],
        y=max_loc[1],
        width=tw,
        height=th,
        confidence=max_val,
        name="grayscale_match",
    )


def match_binary(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    binary_threshold: int = 127,
) -> Box | None:
    """二值化模板匹配

    将图像二值化后进行匹配，适用于高对比度场景。

    Args:
        frame: 源图像
        template: 模板图像
        threshold: 匹配阈值
        binary_threshold: 二值化阈值

    Returns:
        匹配到的 Box
    """
    frame_binary = to_binary(frame, binary_threshold)
    template_binary = to_binary(template, binary_threshold)

    th, tw = template_binary.shape[:2]
    result = cv2.matchTemplate(frame_binary, template_binary, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    return Box(
        x=max_loc[0],
        y=max_loc[1],
        width=tw,
        height=th,
        confidence=max_val,
        name="binary_match",
    )


def match_edge(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.7,
) -> Box | None:
    """边缘模板匹配

    使用边缘检测后的图像进行匹配，对光照变化更鲁棒。

    Args:
        frame: 源图像
        template: 模板图像
        threshold: 匹配阈值

    Returns:
        匹配到的 Box
    """
    frame_edge = edge_detection(frame)
    template_edge = edge_detection(template)

    th, tw = template_edge.shape[:2]
    result = cv2.matchTemplate(frame_edge, template_edge, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    return Box(
        x=max_loc[0],
        y=max_loc[1],
        width=tw,
        height=th,
        confidence=max_val,
        name="edge_match",
    )


def find_shapes(
    image: np.ndarray,
    shape_type: str = "rectangle",
    min_area: int = 100,
    max_area: int | None = None,
) -> list[Box]:
    """检测形状

    Args:
        image: 输入图像
        shape_type: 形状类型 ('rectangle', 'circle', 'triangle', 'any')
        min_area: 最小面积
        max_area: 最大面积

    Returns:
        检测到的形状区域
    """
    gray = to_grayscale(image)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results: list[Box] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        if max_area is not None and area > max_area:
            continue

        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        vertices = len(approx)

        if shape_type == "triangle" and vertices != 3:
            continue
        elif shape_type == "rectangle" and vertices != 4:
            continue
        elif shape_type == "circle" and vertices < 8:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        results.append(
            Box(
                x=x,
                y=y,
                width=w,
                height=h,
                confidence=1.0,
                name=f"shape_{shape_type}",
            )
        )

    return results


def compare_histograms(
    image1: np.ndarray,
    image2: np.ndarray,
    method: int = cv2.HISTCMP_CORREL,
) -> float:
    """直方图比较

    Args:
        image1: 图像1
        image2: 图像2
        method: 比较方法

    Returns:
        相似度分数
    """
    hsv1 = cv2.cvtColor(image1, cv2.COLOR_BGR2HSV) if len(image1.shape) == 3 else image1
    hsv2 = cv2.cvtColor(image2, cv2.COLOR_BGR2HSV) if len(image2.shape) == 3 else image2

    h_bins, s_bins = 50, 60
    hist_size = [h_bins, s_bins]
    ranges = [0, 180, 0, 256]
    channels = [0, 1]

    hist1 = cv2.calcHist([hsv1], channels, None, hist_size, ranges)
    hist2 = cv2.calcHist([hsv2], channels, None, hist_size, ranges)

    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

    return cv2.compareHist(hist1, hist2, method)


def detect_text_regions(
    image: np.ndarray,
    min_area: int = 50,
    aspect_ratio_range: tuple[float, float] = (0.1, 10.0),
) -> list[Box]:
    """检测可能的文本区域

    使用形态学方法检测文本区域。

    Args:
        image: 输入图像
        min_area: 最小面积
        aspect_ratio_range: 宽高比范围

    Returns:
        可能的文本区域
    """
    gray = to_grayscale(image)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(otsu_threshold(gray), kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results: list[Box] = []
    min_ratio, max_ratio = aspect_ratio_range

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area:
            continue

        ratio = w / h if h > 0 else 0
        if ratio < min_ratio or ratio > max_ratio:
            continue

        results.append(
            Box(
                x=x,
                y=y,
                width=w,
                height=h,
                confidence=1.0,
                name="text_region",
            )
        )

    return results
