"""Color detection helpers."""

from __future__ import annotations

import cv2
import numpy as np

from .box import Box


def find_color(
    frame: np.ndarray,
    color_lower: tuple[int, int, int],
    color_upper: tuple[int, int, int],
    color_space: str = "BGR",
    min_area: int = 10,
) -> list[Box]:
    """Find regions matching a color range."""
    if color_space.upper() == "HSV":
        frame_converted = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    else:
        frame_converted = frame

    lower = np.array(color_lower)
    upper = np.array(color_upper)
    mask = cv2.inRange(frame_converted, lower, upper)

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
