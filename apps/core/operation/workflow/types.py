"""
工作流基础类型

定义动作状态、触发器类型等基础枚举和数据类。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from operation.service import OperationService


class ActionStatus(Enum):
    """动作状态"""

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    TIMEOUT = auto()


class TriggerType(Enum):
    """触发器类型"""

    ALWAYS = auto()
    TEMPLATE = auto()
    COLOR = auto()
    CONDITION = auto()
    INTERVAL = auto()
    HOTKEY = auto()


@dataclass
class ActionResult:
    """动作执行结果"""

    status: ActionStatus
    message: str = ""
    data: Any = None
    duration: float = 0.0


@dataclass
class TriggerConfig:
    """触发器配置"""

    trigger_type: TriggerType
    template: str | None = None
    threshold: float = 0.8
    color_lower: tuple[int, int, int] | None = None
    color_upper: tuple[int, int, int] | None = None
    condition: Callable[[OperationService], bool] | None = None
    interval: float = 1.0
    hotkey: str | None = None
