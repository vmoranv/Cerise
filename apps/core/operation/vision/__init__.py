"""
视觉分析模块

提供图像处理、模板匹配、OCR等视觉分析能力。
"""

from .box import Box
from .box_utils import (
    find_box_by_name,
    find_boxes_by_name,
    find_boxes_within_boundary,
    find_highest_confidence_box,
    get_bounding_box,
    sort_boxes,
)
from .matching import (
    compare_histograms,
    detect_text_regions,
    find_shapes,
    match_binary,
    match_edge,
    match_grayscale,
)
from .ocr import (
    BaseOCR,
    OCREngine,
    OCRPreprocessor,
    OCRResult,
    OCRService,
    PaddleOCREngine,
    RapidOCREngine,
    TesseractOCREngine,
)
from .preprocessing import (
    adaptive_threshold,
    blur,
    denoise,
    edge_detection,
    otsu_threshold,
    resize,
    sharpen,
    to_binary,
    to_grayscale,
)
from .template import (
    find_color,
    load_template,
    load_template_with_mask,
    match_template,
    match_template_all,
    match_template_multi_scale,
)

__all__ = [
    # Box
    "Box",
    "find_box_by_name",
    "find_boxes_by_name",
    "find_boxes_within_boundary",
    "find_highest_confidence_box",
    "get_bounding_box",
    "sort_boxes",
    # Preprocessing
    "to_grayscale",
    "to_binary",
    "adaptive_threshold",
    "otsu_threshold",
    "edge_detection",
    "denoise",
    "sharpen",
    "blur",
    "resize",
    # Matching
    "match_grayscale",
    "match_binary",
    "match_edge",
    "find_shapes",
    "compare_histograms",
    "detect_text_regions",
    # OCR
    "OCRResult",
    "OCREngine",
    "OCRPreprocessor",
    "BaseOCR",
    "OCRService",
    "PaddleOCREngine",
    "RapidOCREngine",
    "TesseractOCREngine",
    # Template matching
    "find_color",
    "load_template",
    "load_template_with_mask",
    "match_template",
    "match_template_all",
    "match_template_multi_scale",
]
