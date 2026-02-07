"""Vision-related mixin for operation service."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from apps.core.contracts.events import OPERATION_TEMPLATE_MATCHED, build_operation_template_matched

from .vision.box import Box
from .vision.template import find_color, load_template, match_template, match_template_all


class OperationVisionMixin:
    """Template matching and vision helpers."""

    _template_cache: dict[str, np.ndarray]
    _template_dir: Path | None

    def _publish_event(self, event_type: str, data: dict[str, object]) -> None:
        raise NotImplementedError

    @staticmethod
    def _box_payload(box: Box) -> dict[str, object]:
        raise NotImplementedError

    def get_frame(self) -> np.ndarray | None:
        raise NotImplementedError

    def _get_template(self, template: str | np.ndarray) -> np.ndarray | None:
        """Get template image with cache."""
        if isinstance(template, np.ndarray):
            return template

        if template in self._template_cache:
            return self._template_cache[template]

        path = Path(template)
        if not path.is_absolute() and self._template_dir is not None:
            path = self._template_dir / template

        template_img = load_template(path)
        if template_img is not None:
            self._template_cache[template] = template_img
        return template_img

    def find_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        frame: np.ndarray | None = None,
        region: Box | None = None,
        name: str | None = None,
    ) -> Box | None:
        """Find a template in the current frame."""
        template_img = self._get_template(template)
        if template_img is None:
            return None

        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return None

        offset_x, offset_y = 0, 0
        if region is not None:
            frame = region.crop_frame(frame)
            offset_x, offset_y = region.x, region.y

        result = match_template(frame, template_img, threshold=threshold, name=name)

        if result is not None and (offset_x != 0 or offset_y != 0):
            result = result.copy(x_offset=offset_x, y_offset=offset_y)

        if result is not None:
            template_name = template if isinstance(template, str) else "<array>"
            self._publish_event(
                OPERATION_TEMPLATE_MATCHED,
                build_operation_template_matched(
                    template=template_name,
                    threshold=threshold,
                    box=self._box_payload(result),
                ),
            )

        return result

    def find_all_templates(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        frame: np.ndarray | None = None,
        region: Box | None = None,
        name: str | None = None,
        max_results: int = 100,
    ) -> list[Box]:
        """Find all template matches."""
        template_img = self._get_template(template)
        if template_img is None:
            return []

        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return []

        offset_x, offset_y = 0, 0
        if region is not None:
            frame = region.crop_frame(frame)
            offset_x, offset_y = region.x, region.y

        results = match_template_all(frame, template_img, threshold=threshold, name=name, max_results=max_results)

        if offset_x != 0 or offset_y != 0:
            results = [box.copy(x_offset=offset_x, y_offset=offset_y) for box in results]

        return results

    def wait_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        timeout: float = 10.0,
        interval: float = 0.1,
        region: Box | None = None,
        name: str | None = None,
    ) -> Box | None:
        """Wait for a template to appear."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.find_template(template, threshold=threshold, region=region, name=name)
            if result is not None:
                return result
            time.sleep(interval)
        return None

    def find_color(
        self,
        color_lower: tuple[int, int, int],
        color_upper: tuple[int, int, int],
        color_space: str = "BGR",
        min_area: int = 10,
        frame: np.ndarray | None = None,
        region: Box | None = None,
    ) -> list[Box]:
        """Find regions matching a color range."""
        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return []

        offset_x, offset_y = 0, 0
        if region is not None:
            frame = region.crop_frame(frame)
            offset_x, offset_y = region.x, region.y

        results = find_color(frame, color_lower, color_upper, color_space, min_area)

        if offset_x != 0 or offset_y != 0:
            results = [box.copy(x_offset=offset_x, y_offset=offset_y) for box in results]

        return results
