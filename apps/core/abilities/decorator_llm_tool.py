"""LLM tool decorator helpers."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable

from .base import AbilityCategory, AbilityContext, AbilityResult, AbilityType, BaseAbility
from .decorator_schema import extract_description, extract_schema_from_docstring
from .registry import AbilityRegistry

logger = logging.getLogger(__name__)


def llm_tool(
    name: str,
    *,
    description: str = "",
):
    """
    Decorator to register a function as an LLM tool.

    The function docstring is used as the description if not provided.
    Parameters are extracted from the function signature and docstring.
    """

    def decorator(func: Callable) -> Callable:
        doc = func.__doc__ or ""
        desc = description or extract_description(doc)
        params_schema = extract_schema_from_docstring(func)

        class ToolAbility(BaseAbility):
            @property
            def name(self) -> str:
                return name

            @property
            def display_name(self) -> str:
                return name.replace("_", " ").title()

            @property
            def description(self) -> str:
                return desc

            @property
            def ability_type(self) -> AbilityType:
                return AbilityType.BUILTIN

            @property
            def category(self) -> AbilityCategory:
                return AbilityCategory.UTILITY

            @property
            def parameters_schema(self) -> dict:
                return params_schema

            async def execute(
                self,
                params: dict,
                context: AbilityContext,
            ) -> AbilityResult:
                try:
                    result = await func(**params)
                    return AbilityResult(success=True, data=result)
                except Exception as e:
                    return AbilityResult(success=False, error=str(e))

        ability_instance = ToolAbility()
        AbilityRegistry.register(ability_instance)
        logger.debug("Registered LLM tool: %s", name)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._ability_instance = ability_instance
        return wrapper

    return decorator
