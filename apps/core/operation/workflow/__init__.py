"""
工作流模块

提供任务定义、动作序列、条件触发等自动化工作流能力。
"""

from .actions import (
    Action,
    ClickAction,
    ConditionalAction,
    KeyPressAction,
    LoopAction,
    TypeTextAction,
    WaitAction,
)
from .manager import ActionSequence, Task, Workflow
from .types import (
    ActionResult,
    ActionStatus,
    TriggerConfig,
    TriggerType,
)

__all__ = [
    # Types
    "ActionResult",
    "ActionStatus",
    "TriggerConfig",
    "TriggerType",
    # Actions
    "Action",
    "ClickAction",
    "ConditionalAction",
    "KeyPressAction",
    "LoopAction",
    "TypeTextAction",
    "WaitAction",
    # Manager
    "ActionSequence",
    "Task",
    "Workflow",
]
