"""
OCR 图像预处理器
"""

from __future__ import annotations

import numpy as np

from operation.vision.preprocessing import (
    adaptive_threshold,
    denoise,
    resize,
    to_grayscale,
)


class OCRPreprocessor:
    """OCR 预处理器

    提供图像预处理以提高 OCR 识别率。
    """

    def __init__(
        self,
        grayscale: bool = True,
        denoise_strength: float = 5.0,
        binarize: bool = False,
        upscale: float = 1.0,
    ) -> None:
        self.grayscale = grayscale
        self.denoise_strength = denoise_strength
        self.binarize = binarize
        self.upscale = upscale

    def process(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        result = image.copy()

        if self.upscale > 1.0:
            result = resize(result, scale=self.upscale)

        if self.denoise_strength > 0:
            result = denoise(result, h=self.denoise_strength)

        if self.grayscale and len(result.shape) == 3:
            result = to_grayscale(result)

        if self.binarize:
            result = adaptive_threshold(result)

        return result
