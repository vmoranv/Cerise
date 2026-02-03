"""
任务与工作流管理

提供任务定义、动作序列、工作流管理器。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .actions import Action
from .types import ActionResult, ActionStatus, CancelToken, TriggerConfig, TriggerType

if TYPE_CHECKING:
    from ..service import OperationService


@dataclass
class ActionSequence:
    """动作序列"""

    name: str
    actions: list[Action] = field(default_factory=list)
    stop_on_failure: bool = True

    def add(self, action: Action) -> ActionSequence:
        self.actions.append(action)
        return self

    def execute(
        self,
        service: OperationService,
        *,
        cancel_token: CancelToken | None = None,
        timeout: float | None = None,
    ) -> list[ActionResult]:
        results: list[ActionResult] = []
        start = time.time()
        effective_timeout = timeout
        if effective_timeout is None:
            effective_timeout = 0.0
        deadline = start + float(effective_timeout) if effective_timeout and effective_timeout > 0 else None
        for action in self.actions:
            if cancel_token and cancel_token.cancelled:
                result = ActionResult(ActionStatus.SKIPPED, cancel_token.reason or "Cancelled", duration=0.0)
                action.result = result
                action.status = result.status
                results.append(result)
                service.emit_action_result(action, result)
                break
            if deadline is not None and time.time() > deadline:
                result = ActionResult(ActionStatus.TIMEOUT, "Sequence timeout", duration=0.0)
                action.result = result
                action.status = result.status
                results.append(result)
                service.emit_action_result(action, result)
                break

            action.status = ActionStatus.RUNNING
            result = action.execute(service, cancel_token)
            action.result = result
            action.status = result.status
            results.append(result)
            service.emit_action_result(action, result)
            if self.stop_on_failure and result.status == ActionStatus.FAILED:
                break
        return results

    def reset(self) -> None:
        for action in self.actions:
            action.reset()


@dataclass
class Task:
    """任务定义"""

    name: str
    trigger: TriggerConfig
    sequence: ActionSequence
    enabled: bool = True
    priority: int = 0
    cooldown: float = 0.0
    _last_run: float = field(default=0.0, repr=False)

    def check_trigger(self, service: OperationService) -> bool:
        if not self.enabled:
            return False
        if self.cooldown > 0 and time.time() - self._last_run < self.cooldown:
            return False

        t = self.trigger
        if t.trigger_type == TriggerType.ALWAYS:
            return True
        elif t.trigger_type == TriggerType.TEMPLATE and t.template:
            return service.find_template(t.template, t.threshold) is not None
        elif t.trigger_type == TriggerType.COLOR and t.color_lower and t.color_upper:
            return len(service.find_color(t.color_lower, t.color_upper)) > 0
        elif t.trigger_type == TriggerType.CONDITION and t.condition:
            return t.condition(service)
        return False

    def execute(self, service: OperationService) -> list[ActionResult]:
        self._last_run = time.time()
        return self.sequence.execute(service)


class Workflow:
    """工作流管理器"""

    def __init__(self, name: str = "Workflow") -> None:
        self.name = name
        self.tasks: list[Task] = []
        self.running = False
        self._stop_flag = False

    def add_task(self, task: Task) -> Workflow:
        self.tasks.append(task)
        self.tasks.sort(key=lambda t: t.priority, reverse=True)
        return self

    def remove_task(self, name: str) -> bool:
        for i, task in enumerate(self.tasks):
            if task.name == name:
                self.tasks.pop(i)
                return True
        return False

    def get_task(self, name: str) -> Task | None:
        for task in self.tasks:
            if task.name == name:
                return task
        return None

    def stop(self) -> None:
        self._stop_flag = True

    def run(
        self,
        service: OperationService,
        max_iterations: int = 0,
        interval: float = 0.1,
        on_task_start: Callable[[Task], None] | None = None,
        on_task_complete: Callable[[Task, list[ActionResult]], None] | None = None,
    ) -> None:
        self.running = True
        self._stop_flag = False
        iterations = 0

        while not self._stop_flag:
            if max_iterations > 0 and iterations >= max_iterations:
                break

            for task in self.tasks:
                if self._stop_flag:
                    break
                if task.check_trigger(service):
                    if on_task_start:
                        on_task_start(task)
                    results = task.execute(service)
                    if on_task_complete:
                        on_task_complete(task, results)
                    break

            iterations += 1
            time.sleep(interval)

        self.running = False

    async def run_async(
        self,
        service: OperationService,
        max_iterations: int = 0,
        interval: float = 0.1,
    ) -> None:
        self.running = True
        self._stop_flag = False
        iterations = 0

        while not self._stop_flag:
            if max_iterations > 0 and iterations >= max_iterations:
                break

            for task in self.tasks:
                if self._stop_flag:
                    break
                if task.check_trigger(service):
                    task.execute(service)
                    break

            iterations += 1
            await asyncio.sleep(interval)

        self.running = False
