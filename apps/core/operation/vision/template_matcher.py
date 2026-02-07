"""Template matching helpers."""

from __future__ import annotations

import cv2
import numpy as np

from .box import Box


def match_template(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED,
    name: str | None = None,
) -> Box | None:
    """Match template and return best match."""
    if len(frame.shape) == 3:
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        frame_gray = frame

    if len(template.shape) == 3:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template

    th, tw = template_gray.shape[:2]
    fh, fw = frame_gray.shape[:2]

    if tw > fw or th > fh:
        return None

    result = cv2.matchTemplate(frame_gray, template_gray, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

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
    """Match template and return all matches."""
    if len(frame.shape) == 3:
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        frame_gray = frame

    if len(template.shape) == 3:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template

    th, tw = template_gray.shape[:2]
    fh, fw = frame_gray.shape[:2]

    if tw > fw or th > fh:
        return []

    result = cv2.matchTemplate(frame_gray, template_gray, method)

    if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
        locations = np.where(result <= (1.0 - threshold))
        confidences = [1.0 - result[y, x] for y, x in zip(*locations)]
    else:
        locations = np.where(result >= threshold)
        confidences = [result[y, x] for y, x in zip(*locations)]

    if len(confidences) == 0:
        return []

    boxes_for_nms: list[list[int]] = []
    for y, x in zip(*locations):
        boxes_for_nms.append([x, y, x + tw, y + th])

    boxes_for_nms_arr = np.array(boxes_for_nms)
    confidences_arr = np.array(confidences)

    indices = cv2.dnn.NMSBoxes(
        boxes_for_nms_arr.tolist(),
        confidences_arr.tolist(),
        threshold,
        nms_threshold,
    )

    if len(indices) == 0:
        return []

    results: list[Box] = []
    flattened_indices = np.array(indices).flatten()
    for i in flattened_indices[:max_results]:
        idx = int(i)
        x, y = boxes_for_nms_arr[idx][:2]
        results.append(
            Box(
                x=int(x),
                y=int(y),
                width=tw,
                height=th,
                confidence=float(confidences_arr[idx]),
                name=name,
            )
        )

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
    """Multi-scale template matching."""
    if scales is None:
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]

    best_box: Box | None = None
    best_confidence = 0.0

    th, tw = template.shape[:2]

    for scale in scales:
        new_w = int(tw * scale)
        new_h = int(th * scale)

        if new_w < 1 or new_h < 1:
            continue

        scaled_template = cv2.resize(template, (new_w, new_h))

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
