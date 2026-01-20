"""Ability decorator helpers."""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable

from .base import AbilityCategory, AbilityContext, AbilityResult, AbilityType, BaseAbility
from .decorator_schema import extract_schema_from_signature
from .registry import AbilityRegistry

logger = logging.getLogger(__name__)


def ability(
    name: str,
    *,
    display_name: str = "",
    description: str = "",
    category: AbilityCategory = AbilityCategory.UTILITY,
    permissions: list[str] | None = None,
):
    """
    Decorator to register a function as an ability.

    Usage:
        @ability("my_ability", display_name="My Ability", description="Does something")
        async def my_ability(params: dict, context: AbilityContext) -> AbilityResult:
            ...
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        parameters_schema = extract_schema_from_signature(sig, func)

        class FunctionAbility(BaseAbility):
            @property
            def name(self) -> str:
                return name

            @property
            def display_name(self) -> str:
                return display_name or name.replace("_", " ").title()

            @property
            def description(self) -> str:
                return description or func.__doc__ or ""

            @property
            def ability_type(self) -> AbilityType:
                return AbilityType.BUILTIN

            @property
            def category(self) -> AbilityCategory:
                return category

            @property
            def parameters_schema(self) -> dict:
                return parameters_schema

            @property
            def required_permissions(self) -> list[str]:
                return permissions or []

            async def execute(
                self,
                params: dict,
                context: AbilityContext,
            ) -> AbilityResult:
                return await func(params, context)

        ability_instance = FunctionAbility()
        AbilityRegistry.register(ability_instance)
        logger.debug("Registered ability: %s", name)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._ability_instance = ability_instance
        return wrapper

    return decorator
