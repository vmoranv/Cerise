"""
Box - 屏幕区域抽象

表示屏幕上的一个矩形区域，用于标识 UI 元素、图像特征等。
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from functools import cmp_to_key
from re import Pattern
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np


@dataclass
class Box:
    """屏幕区域类

    Attributes:
        x: 矩形左上角 x 坐标
        y: 矩形左上角 y 坐标
        width: 矩形宽度
        height: 矩形高度
        confidence: 置信度 (0.0-1.0)
        name: 区域名称/标识符
    """

    x: int
    y: int
    width: int = 1
    height: int = 1
    confidence: float = 1.0
    name: str | None = None

    def __post_init__(self) -> None:
        self.x = int(round(self.x))
        self.y = int(round(self.y))
        self.width = int(round(self.width))
        self.height = int(round(self.height))

        if self.width <= 0:
            self.width = 1
        if self.height <= 0:
            self.height = 1

    @classmethod
    def from_coords(
        cls,
        x: int,
        y: int,
        to_x: int,
        to_y: int,
        confidence: float = 1.0,
        name: str | None = None,
    ) -> Box:
        """从左上角和右下角坐标创建 Box"""
        return cls(
            x=x,
            y=y,
            width=to_x - x,
            height=to_y - y,
            confidence=confidence,
            name=name,
        )

    @classmethod
    def from_relative(
        cls,
        frame_width: int,
        frame_height: int,
        x: float,
        y: float,
        to_x: float = 1.0,
        to_y: float = 1.0,
        confidence: float = 1.0,
        name: str | None = None,
    ) -> Box:
        """从相对坐标 (0.0-1.0) 创建 Box"""
        return cls(
            x=int(round(x * frame_width)),
            y=int(round(y * frame_height)),
            width=int(round((to_x - x) * frame_width)),
            height=int(round((to_y - y) * frame_height)),
            confidence=confidence,
            name=name,
        )

    @property
    def to_x(self) -> int:
        """右下角 x 坐标"""
        return self.x + self.width

    @property
    def to_y(self) -> int:
        """右下角 y 坐标"""
        return self.y + self.height

    def area(self) -> int:
        """计算矩形面积"""
        return self.width * self.height

    def center(self) -> tuple[int, int]:
        """计算中心点坐标"""
        return (
            round(self.x + self.width / 2.0),
            round(self.y + self.height / 2.0),
        )

    def center_with_variance(
        self,
        relative_x: float = 0.5,
        relative_y: float = 0.5,
        variance: float = 0.1,
    ) -> tuple[int, int]:
        """计算带随机偏移的相对位置

        Args:
            relative_x: 相对于宽度的 x 比例 (0.0-1.0)
            relative_y: 相对于高度的 y 比例 (0.0-1.0)
            variance: 随机偏移范围

        Returns:
            带随机偏移的坐标
        """
        center_x = self.x + self.width * relative_x
        center_y = self.y + self.height * relative_y
        offset = random.uniform(0, variance)
        return int(round(center_x + offset)), int(round(center_y + offset))

    def scale(self, width_ratio: float, height_ratio: float | None = None) -> Box:
        """按比例缩放 Box，保持中心点不变

        Args:
            width_ratio: 宽度缩放比例 (1.1 = 110%, 0.9 = 90%)
            height_ratio: 高度缩放比例，默认使用 width_ratio

        Returns:
            缩放后的新 Box
        """
        if height_ratio is None:
            height_ratio = width_ratio

        center_x, center_y = self.center()
        new_width = round(self.width * width_ratio)
        new_height = round(self.height * height_ratio)
        new_x = max(0, round(center_x - new_width / 2.0))
        new_y = max(0, round(center_y - new_height / 2.0))

        return Box(
            x=new_x,
            y=new_y,
            width=new_width,
            height=new_height,
            confidence=self.confidence,
            name=self.name,
        )

    def copy(
        self,
        x_offset: int = 0,
        y_offset: int = 0,
        width_offset: int = 0,
        height_offset: int = 0,
        name: str | None = None,
    ) -> Box:
        """创建带偏移的副本"""
        return Box(
            x=self.x + x_offset,
            y=self.y + y_offset,
            width=self.width + width_offset,
            height=self.height + height_offset,
            confidence=self.confidence,
            name=name or self.name,
        )

    def crop_frame(self, frame: np.ndarray) -> np.ndarray:
        """从图像帧中裁剪出此区域

        Args:
            frame: numpy 图像数组

        Returns:
            裁剪后的图像区域
        """
        return frame[self.y : self.y + self.height, self.x : self.x + self.width]

    def center_distance(self, other: Box) -> float:
        """计算与另一个 Box 中心点的距离"""
        x1, y1 = self.center()
        x2, y2 = other.center()
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(float(dx**2 + dy**2))

    def closest_distance(self, other: Box) -> float:
        """计算与另一个 Box 的最近边距离"""
        horizontal_distance = max(0, max(self.x, other.x) - min(self.to_x, other.to_x))
        vertical_distance = max(0, max(self.y, other.y) - min(self.to_y, other.to_y))

        if horizontal_distance == 0 and vertical_distance == 0:
            return 0.0
        return math.sqrt(horizontal_distance**2 + vertical_distance**2)

    def contains(self, other: Box) -> bool:
        """检查是否完全包含另一个 Box"""
        return self.x <= other.x and self.y <= other.y and self.to_x >= other.to_x and self.to_y >= other.to_y

    def intersects(self, other: Box) -> bool:
        """检查是否与另一个 Box 相交"""
        return not (self.to_x < other.x or other.to_x < self.x or self.to_y < other.y or other.to_y < self.y)

    def find_closest_box(
        self,
        direction: str,
        boxes: list[Box],
        condition: Any | None = None,
    ) -> Box | None:
        """在指定方向上查找最近的 Box

        Args:
            direction: 方向 ('up', 'down', 'left', 'right', 'all')
            boxes: 要搜索的 Box 列表
            condition: 可选的过滤函数

        Returns:
            最近的 Box，未找到返回 None
        """

        def distance_criteria(box: Box) -> float:
            if box is self:
                return float("inf")

            # 方向过滤
            if direction == "up" and self.y - (box.y + box.height / 2) < 0:
                return float("inf")
            elif direction == "down" and box.y - (self.y + self.height / 2) < 0:
                return float("inf")
            elif direction == "left" and self.x - (box.x + box.width / 2) < 0:
                return float("inf")
            elif direction == "right" and box.x - (self.x + self.width / 2) < 0:
                return float("inf")

            if condition is not None and not condition(box):
                return float("inf")

            return self.closest_distance(box)

        sorted_boxes = sorted(boxes, key=distance_criteria)
        for box in sorted_boxes:
            if distance_criteria(box) != float("inf"):
                return box
        return None

    def __repr__(self) -> str:
        if self.name:
            return f"{self.name}_{self.confidence:.2f}"
        return f"Box({self.x},{self.y},{self.width}x{self.height})"

    def __str__(self) -> str:
        if self.name is not None:
            return (
                f"Box(name='{self.name}', x={self.x}, y={self.y}, "
                f"width={self.width}, height={self.height}, "
                f"confidence={round(self.confidence * 100)}%)"
            )
        return (
            f"Box(x={self.x}, y={self.y}, width={self.width}, "
            f"height={self.height}, confidence={round(self.confidence * 100)}%)"
        )


# ============ Box 集合操作函数 ============


def find_box_by_name(
    boxes: list[Box],
    names: str | Pattern[str] | list[str | Pattern[str]],
) -> Box | None:
    """根据名称查找 Box

    Args:
        boxes: Box 列表
        names: 要匹配的名称/正则表达式（支持列表，按优先级排序）

    Returns:
        匹配的 Box，未找到返回 None
    """
    if isinstance(names, (str, Pattern)):
        names = [names]

    result: Box | None = None
    priority = len(names)

    for box in boxes:
        if box.name is None:
            continue
        for i, name in enumerate(names):
            if isinstance(name, str) and name == box.name:
                if i < priority:
                    priority = i
                    result = box
                    if i == 0:
                        return result
            elif isinstance(name, Pattern) and re.search(name, box.name):
                if i < priority:
                    priority = i
                    result = box
                    if i == 0:
                        return result

    return result


def find_boxes_by_name(
    boxes: list[Box],
    names: str | Pattern[str] | list[str | Pattern[str]],
) -> list[Box]:
    """根据名称查找所有匹配的 Box"""
    if isinstance(names, (str, Pattern)):
        names = [names]

    result: list[Box] = []

    for box in boxes:
        if box.name is None:
            continue
        for name in names:
            if isinstance(name, str) and name == box.name:
                result.append(box)
                break
            elif isinstance(name, Pattern) and re.search(name, box.name):
                result.append(box)
                break

    return result


def find_highest_confidence_box(boxes: list[Box]) -> Box | None:
    """找到置信度最高的 Box"""
    if not boxes:
        return None
    return max(boxes, key=lambda box: box.confidence)


def find_boxes_within_boundary(
    boxes: list[Box],
    boundary: Box,
    sort: bool = True,
) -> list[Box]:
    """查找边界内的所有 Box"""
    within = [box for box in boxes if boundary.contains(box)]
    if sort:
        within = sort_boxes(within)
    return within


def get_bounding_box(boxes: list[Box]) -> Box:
    """获取包含所有 Box 的最小边界框"""
    if not boxes:
        raise ValueError("boxes 列表不能为空")

    min_x = min(box.x for box in boxes)
    min_y = min(box.y for box in boxes)
    max_x = max(box.to_x for box in boxes)
    max_y = max(box.to_y for box in boxes)

    return Box(min_x, min_y, max_x - min_x, max_y - min_y)


def sort_boxes(boxes: list[Box]) -> list[Box]:
    """排序 Box（按阅读顺序：从上到下，从左到右）"""

    def compare(box1: Box, box2: Box) -> int:
        # 检查是否在同一行（y 坐标有交集）
        intersect_y = not (box1.to_y < box2.y or box2.to_y < box1.y)

        if intersect_y:
            cmp = box1.x - box2.x
            if cmp == 0:
                cmp = box1.y - box2.y
        else:
            cmp = box1.y - box2.y
            if cmp == 0:
                cmp = box1.x - box2.x

        if cmp == 0:
            cmp = int(box1.confidence * 1000 - box2.confidence * 1000)

        if cmp == 0 and box1.name and box2.name:
            cmp = (box1.name > box2.name) - (box1.name < box2.name)

        return cmp

    return sorted(boxes, key=cmp_to_key(compare))
