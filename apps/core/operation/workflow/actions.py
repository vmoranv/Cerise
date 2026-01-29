"""
动作定义

提供各种预定义动作类。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from .types import ActionResult, ActionStatus

if TYPE_CHECKING:
    from ..service import OperationService


class Action(ABC):
    """动作基类"""

    def __init__(self, name: str = "", timeout: float = 30.0) -> None:
        self.name = name or self.__class__.__name__
        self.timeout = timeout
        self.status = ActionStatus.PENDING
        self.result: ActionResult | None = None

    @abstractmethod
    def execute(self, service: OperationService) -> ActionResult: ...

    def reset(self) -> None:
        self.status = ActionStatus.PENDING
        self.result = None


class ClickAction(Action):
    """点击动作"""

    def __init__(
        self,
        x: int | None = None,
        y: int | None = None,
        template: str | None = None,
        threshold: float = 0.8,
        button: str = "left",
        wait_before: float = 0.0,
        wait_after: float = 0.1,
        name: str = "",
    ) -> None:
        super().__init__(name or "Click")
        self.x = x
        self.y = y
        self.template = template
        self.threshold = threshold
        self.button = button
        self.wait_before = wait_before
        self.wait_after = wait_after

    def execute(self, service: OperationService) -> ActionResult:
        start = time.time()
        if self.wait_before > 0:
            time.sleep(self.wait_before)

        try:
            if self.template:
                box = service.find_template(self.template, self.threshold)
                if box is None:
                    return ActionResult(
                        ActionStatus.FAILED, f"Template not found: {self.template}", duration=time.time() - start
                    )
                service.click_box(box, self.button)
            elif self.x is not None and self.y is not None:
                service.click(self.x, self.y, self.button)
            else:
                return ActionResult(ActionStatus.FAILED, "No target", duration=time.time() - start)

            if self.wait_after > 0:
                time.sleep(self.wait_after)
            return ActionResult(ActionStatus.SUCCESS, "Click executed", duration=time.time() - start)
        except Exception as e:
            return ActionResult(ActionStatus.FAILED, str(e), duration=time.time() - start)


class KeyPressAction(Action):
    """按键动作"""

    def __init__(
        self,
        key: str,
        duration: float = 0.0,
        modifiers: list[str] | None = None,
        wait_after: float = 0.05,
        name: str = "",
    ) -> None:
        super().__init__(name or f"KeyPress({key})")
        self.key = key
        self.duration = duration
        self.modifiers = modifiers or []
        self.wait_after = wait_after

    def execute(self, service: OperationService) -> ActionResult:
        start = time.time()
        try:
            if self.modifiers:
                service.hotkey(*self.modifiers, self.key)
            else:
                service.key_press(self.key, self.duration)
            if self.wait_after > 0:
                time.sleep(self.wait_after)
            return ActionResult(ActionStatus.SUCCESS, f"Key: {self.key}", duration=time.time() - start)
        except Exception as e:
            return ActionResult(ActionStatus.FAILED, str(e), duration=time.time() - start)


class WaitAction(Action):
    """等待动作"""

    def __init__(
        self,
        duration: float = 1.0,
        template: str | None = None,
        threshold: float = 0.8,
        timeout: float = 30.0,
        name: str = "",
    ) -> None:
        super().__init__(name or "Wait", timeout)
        self.duration = duration
        self.template = template
        self.threshold = threshold

    def execute(self, service: OperationService) -> ActionResult:
        start = time.time()
        if self.template:
            box = service.wait_template(self.template, self.threshold, timeout=self.timeout)
            if box is None:
                return ActionResult(
                    ActionStatus.TIMEOUT, f"Template not found: {self.template}", duration=time.time() - start
                )
            return ActionResult(ActionStatus.SUCCESS, "Template found", data=box, duration=time.time() - start)
        time.sleep(self.duration)
        return ActionResult(ActionStatus.SUCCESS, f"Waited {self.duration}s", duration=time.time() - start)


class TypeTextAction(Action):
    """输入文本动作"""

    def __init__(self, text: str, interval: float = 0.0, name: str = "") -> None:
        super().__init__(name or "TypeText")
        self.text = text
        self.interval = interval

    def execute(self, service: OperationService) -> ActionResult:
        start = time.time()
        try:
            service.type_text(self.text, self.interval)
            return ActionResult(ActionStatus.SUCCESS, f"Typed: {self.text[:20]}", duration=time.time() - start)
        except Exception as e:
            return ActionResult(ActionStatus.FAILED, str(e), duration=time.time() - start)


class ConditionalAction(Action):
    """条件动作"""

    def __init__(
        self,
        condition: Callable[[OperationService], bool],
        then_action: Action,
        else_action: Action | None = None,
        name: str = "",
    ) -> None:
        super().__init__(name or "Conditional")
        self.condition = condition
        self.then_action = then_action
        self.else_action = else_action

    def execute(self, service: OperationService) -> ActionResult:
        start = time.time()
        try:
            if self.condition(service):
                result = self.then_action.execute(service)
            elif self.else_action:
                result = self.else_action.execute(service)
            else:
                result = ActionResult(ActionStatus.SKIPPED, "Condition not met")
            result.duration = time.time() - start
            return result
        except Exception as e:
            return ActionResult(ActionStatus.FAILED, str(e), duration=time.time() - start)


class LoopAction(Action):
    """循环动作"""

    def __init__(
        self,
        action: Action,
        count: int = 0,
        until: Callable[[OperationService], bool] | None = None,
        interval: float = 0.0,
        timeout: float = 300.0,
        name: str = "",
    ) -> None:
        super().__init__(name or "Loop", timeout)
        self.action = action
        self.count = count
        self.until = until
        self.interval = interval

    def execute(self, service: OperationService) -> ActionResult:
        start = time.time()
        iterations = 0

        while True:
            if time.time() - start > self.timeout:
                return ActionResult(
                    ActionStatus.TIMEOUT,
                    f"Timeout after {iterations} iterations",
                    data=iterations,
                    duration=time.time() - start,
                )
            if self.count > 0 and iterations >= self.count:
                break
            if self.until and self.until(service):
                break

            result = self.action.execute(service)
            iterations += 1

            if result.status == ActionStatus.FAILED:
                return ActionResult(
                    ActionStatus.FAILED, f"Failed at {iterations}", data=iterations, duration=time.time() - start
                )
            if self.interval > 0:
                time.sleep(self.interval)

        return ActionResult(
            ActionStatus.SUCCESS, f"Completed {iterations} iterations", data=iterations, duration=time.time() - start
        )
