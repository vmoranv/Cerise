"""
Python Runner Ability

Execute Python code in a sandboxed environment.
"""

import asyncio
import sys
from io import StringIO
from typing import Any

from ..base import (
    AbilityCategory,
    AbilityContext,
    AbilityResult,
    AbilityType,
    BaseAbility,
)


class PythonRunnerAbility(BaseAbility):
    """Execute Python code in a sandboxed environment"""

    @property
    def name(self) -> str:
        return "python_runner"

    @property
    def display_name(self) -> str:
        return "Python 代码执行"

    @property
    def description(self) -> str:
        return "在安全沙箱中执行 Python 代码片段，返回执行结果和输出"

    @property
    def ability_type(self) -> AbilityType:
        return AbilityType.BUILTIN

    @property
    def category(self) -> AbilityCategory:
        return AbilityCategory.SYSTEM

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "执行超时时间（秒）",
                },
            },
            "required": ["code"],
        }

    @property
    def required_permissions(self) -> list[str]:
        return ["system.execute"]

    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        code = params["code"]
        timeout = params.get("timeout", 30)

        try:
            result = await asyncio.wait_for(
                self._run_code(code),
                timeout=timeout,
            )
            return result
        except TimeoutError:
            return AbilityResult(
                success=False,
                error=f"Execution timed out after {timeout} seconds",
            )

    async def _run_code(self, code: str) -> AbilityResult:
        """Run code in a restricted environment"""
        # Capture stdout
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Create restricted globals
            restricted_globals: dict[str, Any] = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "isinstance": isinstance,
                    "type": type,
                },
            }

            # Execute code
            exec(code, restricted_globals)

            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            return AbilityResult(
                success=True,
                data={
                    "stdout": stdout_output,
                    "stderr": stderr_output,
                },
                emotion_hint="satisfied" if not stderr_output else "concerned",
            )

        except Exception as e:
            return AbilityResult(
                success=False,
                data={"stdout": stdout_capture.getvalue()},
                error=str(e),
                emotion_hint="confused",
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
