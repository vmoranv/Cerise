"""
Ability Decorators

Decorators for registering abilities and LLM tools.
"""

import functools
import inspect
import logging
from collections.abc import Callable

from .base import (
    AbilityCategory,
    AbilityContext,
    AbilityResult,
    AbilityType,
    BaseAbility,
)
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
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters_schema = _extract_schema_from_signature(sig, func)

        # Create ability wrapper class
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

        # Register the ability
        ability_instance = FunctionAbility()
        AbilityRegistry.register(ability_instance)
        logger.debug(f"Registered ability: {name}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._ability_instance = ability_instance
        return wrapper

    return decorator


def llm_tool(
    name: str,
    *,
    description: str = "",
):
    """
    Decorator to register a function as an LLM tool.

    The function docstring is used as the description if not provided.
    Parameters are extracted from the function signature and docstring.

    Usage:
        @llm_tool("get_weather")
        async def get_weather(location: str) -> str:
            '''
            获取天气信息

            Args:
                location (str): 地点名称
            '''
            return f"{location} 的天气是晴天"
    """

    def decorator(func: Callable) -> Callable:
        # Parse docstring for Args
        doc = func.__doc__ or ""
        desc = description or _extract_description(doc)
        params_schema = _extract_schema_from_docstring(func)

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
        logger.debug(f"Registered LLM tool: {name}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._ability_instance = ability_instance
        return wrapper

    return decorator


def on_event(event_type: str):
    """
    Decorator to subscribe to MessageBus events.

    Usage:
        @on_event("dialogue.user_message")
        async def handle_message(event: Event):
            print(f"User said: {event.data['content']}")
    """
    from ..infrastructure import MessageBus

    def decorator(func: Callable) -> Callable:
        # Subscribe to event
        bus = MessageBus()
        bus.subscribe(event_type, func)
        logger.debug(f"Subscribed to event: {event_type}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _extract_description(docstring: str) -> str:
    """Extract description from docstring (first non-empty line)"""
    lines = docstring.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("Args:"):
            return line
    return ""


def _extract_schema_from_signature(sig: inspect.Signature, func: Callable) -> dict:
    """Extract JSON Schema from function signature"""
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ("params", "context", "self"):
            continue

        prop = {"type": "string"}  # Default type

        # Infer type from annotation
        if param.annotation != inspect.Parameter.empty:
            prop = _python_type_to_json_schema(param.annotation)

        properties[param_name] = prop

        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _extract_schema_from_docstring(func: Callable) -> dict:
    """Extract JSON Schema from docstring Args section"""
    doc = func.__doc__ or ""
    sig = inspect.signature(func)

    properties = {}
    required = []

    # Parse Args section
    in_args = False
    for line in doc.split("\n"):
        line = line.strip()
        if line.startswith("Args:"):
            in_args = True
            continue
        if in_args:
            if not line or line.startswith("Returns:"):
                break
            # Parse "param_name (type): description"
            if ":" in line:
                parts = line.split(":", 1)
                param_part = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""

                # Extract name and type
                if "(" in param_part:
                    name = param_part.split("(")[0].strip()
                    type_str = param_part.split("(")[1].rstrip(")")
                else:
                    name = param_part
                    type_str = "string"

                properties[name] = {
                    "type": _docstring_type_to_json(type_str),
                    "description": desc,
                }
                required.append(name)

    # Fallback to signature
    if not properties:
        return _extract_schema_from_signature(sig, func)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _python_type_to_json_schema(python_type: type) -> dict:
    """Convert Python type annotation to JSON Schema"""
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    return type_map.get(python_type, {"type": "string"})


def _docstring_type_to_json(type_str: str) -> str:
    """Convert docstring type to JSON Schema type"""
    type_map = {
        "str": "string",
        "string": "string",
        "int": "integer",
        "integer": "integer",
        "float": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "list": "array",
        "array": "array",
        "dict": "object",
        "object": "object",
    }
    return type_map.get(type_str.lower(), "string")
