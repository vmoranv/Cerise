"""Box collection helpers."""

from __future__ import annotations

import re
from functools import cmp_to_key
from re import Pattern

from .box import Box


def find_box_by_name(
    boxes: list[Box],
    names: str | Pattern[str] | list[str | Pattern[str]],
) -> Box | None:
    """Find a box by name."""
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
    """Find all boxes matching names."""
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
    """Find the highest confidence box."""
    if not boxes:
        return None
    return max(boxes, key=lambda box: box.confidence)


def find_boxes_within_boundary(
    boxes: list[Box],
    boundary: Box,
    sort: bool = True,
) -> list[Box]:
    """Find boxes within boundary."""
    within = [box for box in boxes if boundary.contains(box)]
    if sort:
        within = sort_boxes(within)
    return within


def get_bounding_box(boxes: list[Box]) -> Box:
    """Compute bounding box for boxes."""
    if not boxes:
        raise ValueError("boxes list cannot be empty")

    min_x = min(box.x for box in boxes)
    min_y = min(box.y for box in boxes)
    max_x = max(box.to_x for box in boxes)
    max_y = max(box.to_y for box in boxes)

    return Box(min_x, min_y, max_x - min_x, max_y - min_y)


def sort_boxes(boxes: list[Box]) -> list[Box]:
    """Sort boxes by reading order."""

    def compare(box1: Box, box2: Box) -> int:
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
