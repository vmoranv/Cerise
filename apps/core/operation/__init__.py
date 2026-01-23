"""
Cerise 操作层 (Operation Layer)

提供游戏/应用自动化操作能力：
- 屏幕捕获 (capture)
- 输入模拟 (input)
- 视觉分析 (vision)
- 窗口管理 (window)
- 动作工作流 (workflow)

设计参考: ok-script (https://github.com/ok-oldking/ok-script)
"""

# Capture
from operation.capture import CaptureMethod, Win32BitBltCapture

# Input
from operation.input import (
    VK_CODES,
    Interaction,
    KeyBinding,
    KeyMap,
    Win32Interaction,
    create_arrow_preset,
    create_wasd_preset,
)

# Service
from operation.service import OperationService

# Vision
from operation.vision import (
    BaseOCR,
    Box,
    OCREngine,
    OCRPreprocessor,
    OCRResult,
    OCRService,
    PaddleOCREngine,
    RapidOCREngine,
    TesseractOCREngine,
    adaptive_threshold,
    blur,
    compare_histograms,
    denoise,
    detect_text_regions,
    edge_detection,
    find_color,
    find_shapes,
    load_template,
    match_binary,
    match_edge,
    match_grayscale,
    match_template,
    otsu_threshold,
    resize,
    sharpen,
    to_binary,
    to_grayscale,
)

# Window
from operation.window import (
    WindowInfo,
    bring_to_front,
    find_window_by_title,
    find_windows,
    get_window_info,
)

# Workflow
from operation.workflow import (
    Action,
    ActionResult,
    ActionSequence,
    ActionStatus,
    ClickAction,
    ConditionalAction,
    KeyPressAction,
    LoopAction,
    Task,
    TriggerConfig,
    TriggerType,
    TypeTextAction,
    WaitAction,
    Workflow,
)

__all__ = [
    # Main service
    "OperationService",
    # Box
    "Box",
    # Capture
    "CaptureMethod",
    "Win32BitBltCapture",
    # Input
    "Interaction",
    "Win32Interaction",
    "KeyBinding",
    "KeyMap",
    "VK_CODES",
    "create_arrow_preset",
    "create_wasd_preset",
    # Window
    "WindowInfo",
    "bring_to_front",
    "find_window_by_title",
    "find_windows",
    "get_window_info",
    # Vision - Preprocessing
    "to_grayscale",
    "to_binary",
    "adaptive_threshold",
    "otsu_threshold",
    "edge_detection",
    "denoise",
    "sharpen",
    "blur",
    "resize",
    # Vision - Matching
    "match_grayscale",
    "match_binary",
    "match_edge",
    "find_shapes",
    "compare_histograms",
    "detect_text_regions",
    "match_template",
    "find_color",
    "load_template",
    # OCR
    "OCRResult",
    "OCREngine",
    "OCRPreprocessor",
    "BaseOCR",
    "OCRService",
    "PaddleOCREngine",
    "RapidOCREngine",
    "TesseractOCREngine",
    # Workflow
    "Action",
    "ActionResult",
    "ActionSequence",
    "ActionStatus",
    "ClickAction",
    "ConditionalAction",
    "KeyPressAction",
    "LoopAction",
    "Task",
    "TriggerConfig",
    "TriggerType",
    "TypeTextAction",
    "WaitAction",
    "Workflow",
]
