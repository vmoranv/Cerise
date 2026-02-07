"""Factories for operation input components."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast, overload

from .base import Interaction
from .gamepad import Gamepad, NullGamepad
from .null import NullInteraction
from .policy import GamepadPolicy, NullGamepadPolicy
from .policy_callable import PredictCallable
from .win32 import Win32Interaction
from .win32_sendinput import Win32SendInputInteraction

InteractionBackend = Literal["postmessage", "sendinput", "null"]
GamepadBackend = Literal["null", "vgamepad"]
PolicyBackend = Literal["null", "http", "callable"]


def available_interaction_backends() -> list[str]:
    return ["postmessage", "sendinput", "null"]


def available_gamepad_backends() -> list[str]:
    return ["null", "vgamepad"]


def available_policy_backends() -> list[str]:
    return ["null", "http", "callable"]


def create_interaction(backend: InteractionBackend = "postmessage") -> Interaction:
    backend = cast(InteractionBackend, backend.lower().strip())
    if backend == "postmessage":
        return Win32Interaction()
    if backend == "sendinput":
        return Win32SendInputInteraction()
    if backend == "null":
        return NullInteraction()
    raise ValueError(f"Unknown interaction backend: {backend!r}. Available: {available_interaction_backends()}")


def create_gamepad(backend: GamepadBackend = "null") -> Gamepad:
    backend = cast(GamepadBackend, backend.lower().strip())
    if backend == "null":
        return NullGamepad()
    if backend == "vgamepad":
        from .vgamepad_backend import VGamepadGamepad

        return VGamepadGamepad()
    raise ValueError(f"Unknown gamepad backend: {backend!r}. Available: {available_gamepad_backends()}")


@overload
def create_policy(backend: Literal["null"] = "null", **kwargs: object) -> GamepadPolicy:
    pass


@overload
def create_policy(
    backend: Literal["http"],
    *,
    endpoint: str,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    send_frame: bool = True,
) -> GamepadPolicy:
    pass


@overload
def create_policy(backend: Literal["callable"], *, predict: PredictCallable) -> GamepadPolicy:
    pass


def create_policy(backend: PolicyBackend = "null", **kwargs: object) -> GamepadPolicy:
    backend = cast(PolicyBackend, backend.lower().strip())
    if backend == "null":
        if kwargs:
            raise TypeError(f"Unknown create_policy kwargs: {sorted(kwargs.keys())}")
        return NullGamepadPolicy()

    if backend == "http":
        from .policy_http import HttpGamepadPolicy

        endpoint_obj = kwargs.pop("endpoint")
        timeout_obj = kwargs.pop("timeout", 10.0)
        headers_obj = kwargs.pop("headers", None)
        send_frame = bool(kwargs.pop("send_frame", True))
        if kwargs:
            raise TypeError(f"Unknown HttpGamepadPolicy kwargs: {sorted(kwargs.keys())}")
        endpoint = str(endpoint_obj)
        if not isinstance(timeout_obj, (int, float, str)):
            raise TypeError("timeout must be int, float, or string")
        timeout = float(timeout_obj)
        headers: dict[str, str] | None = None
        if headers_obj is not None:
            if not isinstance(headers_obj, Mapping):
                raise TypeError("headers must be a mapping of string keys/values")
            headers = {str(k): str(v) for k, v in headers_obj.items()}
        return HttpGamepadPolicy(endpoint, timeout=timeout, headers=headers, send_frame=send_frame)

    if backend == "callable":
        from .policy_callable import CallableGamepadPolicy

        predict_obj = kwargs.pop("predict")
        if kwargs:
            raise TypeError(f"Unknown CallableGamepadPolicy kwargs: {sorted(kwargs.keys())}")
        if not callable(predict_obj):
            raise TypeError("predict must be callable")
        predict = cast(PredictCallable, predict_obj)
        return CallableGamepadPolicy(predict)

    raise ValueError(f"Unknown policy backend: {backend!r}. Available: {available_policy_backends()}")
