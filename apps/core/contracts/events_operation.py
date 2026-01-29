"""Operation event contracts."""

from __future__ import annotations

from typing import Any, TypedDict

OPERATION_WINDOW_CONNECTED = "operation.window.connected"
OPERATION_WINDOW_DISCONNECTED = "operation.window.disconnected"
OPERATION_INPUT_PERFORMED = "operation.input.performed"
OPERATION_TEMPLATE_MATCHED = "operation.template.matched"
OPERATION_ACTION_COMPLETED = "operation.action.completed"


class OperationWindowConnectedPayload(TypedDict):
    hwnd: int
    width: int
    height: int


def build_operation_window_connected(
    hwnd: int,
    width: int,
    height: int,
) -> OperationWindowConnectedPayload:
    return {"hwnd": hwnd, "width": width, "height": height}


class OperationWindowDisconnectedPayload(TypedDict):
    hwnd: int


def build_operation_window_disconnected(hwnd: int) -> OperationWindowDisconnectedPayload:
    return {"hwnd": hwnd}


class OperationInputPerformedPayload(TypedDict):
    action: str
    hwnd: int
    params: dict[str, Any]


def build_operation_input_performed(
    action: str,
    hwnd: int,
    params: dict[str, Any],
) -> OperationInputPerformedPayload:
    return {"action": action, "hwnd": hwnd, "params": params}


class OperationTemplateMatchedPayload(TypedDict):
    template: str
    threshold: float
    box: dict[str, Any]


def build_operation_template_matched(
    template: str,
    threshold: float,
    box: dict[str, Any],
) -> OperationTemplateMatchedPayload:
    return {"template": template, "threshold": threshold, "box": box}


class OperationActionCompletedPayload(TypedDict):
    action: str
    action_type: str
    status: str
    message: str
    duration: float
    data: dict[str, Any] | None


def build_operation_action_completed(
    action: str,
    action_type: str,
    status: str,
    message: str,
    duration: float,
    data: dict[str, Any] | None = None,
) -> OperationActionCompletedPayload:
    return {
        "action": action,
        "action_type": action_type,
        "status": status,
        "message": message,
        "duration": duration,
        "data": data,
    }


__all__ = [
    "OPERATION_WINDOW_CONNECTED",
    "OPERATION_WINDOW_DISCONNECTED",
    "OPERATION_INPUT_PERFORMED",
    "OPERATION_TEMPLATE_MATCHED",
    "OPERATION_ACTION_COMPLETED",
    "OperationWindowConnectedPayload",
    "OperationWindowDisconnectedPayload",
    "OperationInputPerformedPayload",
    "OperationTemplateMatchedPayload",
    "OperationActionCompletedPayload",
    "build_operation_window_connected",
    "build_operation_window_disconnected",
    "build_operation_input_performed",
    "build_operation_template_matched",
    "build_operation_action_completed",
]
