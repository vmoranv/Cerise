"""
模板匹配视觉分析

使用 OpenCV 进行模板匹配，用于查找屏幕上的图像特征。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from operation.vision.box import Box

if TYPE_CHECKING:
    pass


def match_template(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED,
    name: str | None = None,
) -> Box | None:
    """模板匹配 - 返回最佳匹配

    Args:
        frame: 源图像 (BGR)
        template: 模板图像 (BGR)
        threshold: 匹配阈值 (0.0-1.0)
        method: OpenCV 匹配方法
        name: 返回的 Box 名称

    Returns:
        匹配到的 Box，未找到返回 None
    """
    # 转换为灰度图
    if len(frame.shape) == 3:
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        frame_gray = frame

    if len(template.shape) == 3:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template

    # 检查模板尺寸
    th, tw = template_gray.shape[:2]
    fh, fw = frame_gray.shape[:2]

    if tw > fw or th > fh:
        return None

    # 执行模板匹配
    result = cv2.matchTemplate(frame_gray, template_gray, method)

    # 获取最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 根据匹配方法确定使用的值
    if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
        confidence = 1.0 - min_val
        loc = min_loc
    else:
        confidence = max_val
        loc = max_loc

    if confidence < threshold:
        return None

    return Box(
        x=loc[0],
        y=loc[1],
        width=tw,
        height=th,
        confidence=confidence,
        name=name,
    )


def match_template_all(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED,
    name: str | None = None,
    max_results: int = 100,
    nms_threshold: float = 0.5,
) -> list[Box]:
    """模板匹配 - 返回所有匹配

    Args:
        frame: 源图像 (BGR)
        template: 模板图像 (BGR)
        threshold: 匹配阈值 (0.0-1.0)
        method: OpenCV 匹配方法
        name: 返回的 Box 名称
        max_results: 最大返回数量
        nms_threshold: 非极大值抑制阈值

    Returns:
        匹配到的 Box 列表
    """
    # 转换为灰度图
    if len(frame.shape) == 3:
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        frame_gray = frame

    if len(template.shape) == 3:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template

    # 检查模板尺寸
    th, tw = template_gray.shape[:2]
    fh, fw = frame_gray.shape[:2]

    if tw > fw or th > fh:
        return []

    # 执行模板匹配
    result = cv2.matchTemplate(frame_gray, template_gray, method)

    # 查找所有超过阈值的位置
    if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
        locations = np.where(result <= (1.0 - threshold))
        confidences = [1.0 - result[y, x] for y, x in zip(*locations)]
    else:
        locations = np.where(result >= threshold)
        confidences = [result[y, x] for y, x in zip(*locations)]

    if len(confidences) == 0:
        return []

    # 准备 NMS 输入
    boxes_for_nms = []
    for y, x in zip(*locations):
        boxes_for_nms.append([x, y, x + tw, y + th])

    boxes_for_nms = np.array(boxes_for_nms)
    confidences = np.array(confidences)

    # 应用非极大值抑制
    indices = cv2.dnn.NMSBoxes(
        boxes_for_nms.tolist(),
        confidences.tolist(),
        threshold,
        nms_threshold,
    )

    if len(indices) == 0:
        return []

    # 构建结果
    results: list[Box] = []
    for i in indices.flatten()[:max_results]:
        x, y = boxes_for_nms[i][:2]
        results.append(
            Box(
                x=int(x),
                y=int(y),
                width=tw,
                height=th,
                confidence=float(confidences[i]),
                name=name,
            )
        )

    # 按置信度排序
    results.sort(key=lambda b: b.confidence, reverse=True)
    return results


def match_template_multi_scale(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED,
    name: str | None = None,
    scales: list[float] | None = None,
) -> Box | None:
    """多尺度模板匹配

    Args:
        frame: 源图像 (BGR)
        template: 模板图像 (BGR)
        threshold: 匹配阈值 (0.0-1.0)
        method: OpenCV 匹配方法
        name: 返回的 Box 名称
        scales: 缩放比例列表，默认 [0.8, 0.9, 1.0, 1.1, 1.2]

    Returns:
        最佳匹配的 Box，未找到返回 None
    """
    if scales is None:
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]

    best_box: Box | None = None
    best_confidence = 0.0

    th, tw = template.shape[:2]

    for scale in scales:
        # 缩放模板
        new_w = int(tw * scale)
        new_h = int(th * scale)

        if new_w < 1 or new_h < 1:
            continue

        scaled_template = cv2.resize(template, (new_w, new_h))

        # 执行匹配
        box = match_template(
            frame,
            scaled_template,
            threshold=threshold,
            method=method,
            name=name,
        )

        if box is not None and box.confidence > best_confidence:
            best_confidence = box.confidence
            best_box = box

    return best_box


def load_template(path: str | Path) -> np.ndarray | None:
    """加载模板图像

    Args:
        path: 图像路径

    Returns:
        BGR 格式的图像数组，失败返回 None
    """
    path = Path(path)
    if not path.exists():
        return None

    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return template


def load_template_with_mask(
    path: str | Path,
    mask_path: str | Path | None = None,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """加载模板图像和掩码

    如果模板图像有 alpha 通道，会自动提取为掩码。

    Args:
        path: 模板图像路径
        mask_path: 掩码图像路径（可选）

    Returns:
        (template, mask) 元组
    """
    path = Path(path)
    if not path.exists():
        return None, None

    template = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if template is None:
        return None, None

    mask = None

    # 检查 alpha 通道
    if template.shape[2] == 4:
        # 提取 alpha 通道作为掩码
        mask = template[:, :, 3]
        template = template[:, :, :3]

    # 加载额外的掩码文件
    if mask_path is not None:
        mask_path = Path(mask_path)
        if mask_path.exists():
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

    return template, mask


def find_color(
    frame: np.ndarray,
    color_lower: tuple[int, int, int],
    color_upper: tuple[int, int, int],
    color_space: str = "BGR",
    min_area: int = 10,
) -> list[Box]:
    """颜色查找

    Args:
        frame: 源图像 (BGR)
        color_lower: 颜色下界 (B, G, R) 或 (H, S, V)
        color_upper: 颜色上界
        color_space: 颜色空间 ('BGR' 或 'HSV')
        min_area: 最小区域面积

    Returns:
        匹配的区域列表
    """
    # 转换颜色空间
    if color_space.upper() == "HSV":
        frame_converted = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    else:
        frame_converted = frame

    # 创建掩码
    lower = np.array(color_lower)
    upper = np.array(color_upper)
    mask = cv2.inRange(frame_converted, lower, upper)

    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results: list[Box] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        results.append(
            Box(
                x=x,
                y=y,
                width=w,
                height=h,
                confidence=1.0,
                name="color_match",
            )
        )

    return results
