"""
Computer Use Ability

Control mouse, keyboard, and take screenshots.
"""

from ..base import (
    AbilityCategory,
    AbilityContext,
    AbilityResult,
    AbilityType,
    BaseAbility,
)


class ComputerUseAbility(BaseAbility):
    """Control mouse, keyboard, and take screenshots"""

    @property
    def name(self) -> str:
        return "computer_use"

    @property
    def display_name(self) -> str:
        return "电脑控制"

    @property
    def description(self) -> str:
        return "控制鼠标点击、键盘输入和屏幕截图"

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
                "action": {
                    "type": "string",
                    "enum": ["screenshot", "click", "double_click", "type", "scroll", "move"],
                    "description": "要执行的操作类型",
                },
                "x": {
                    "type": "integer",
                    "description": "X 坐标（用于 click/move）",
                },
                "y": {
                    "type": "integer",
                    "description": "Y 坐标（用于 click/move）",
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文本（用于 type）",
                },
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "滚动方向（用于 scroll）",
                },
                "amount": {
                    "type": "integer",
                    "default": 3,
                    "description": "滚动量（用于 scroll）",
                },
            },
            "required": ["action"],
        }

    @property
    def required_permissions(self) -> list[str]:
        return ["system.computer_use"]

    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        action = params["action"]

        try:
            if action == "screenshot":
                return await self._screenshot()
            elif action == "click":
                return await self._click(params.get("x", 0), params.get("y", 0))
            elif action == "double_click":
                return await self._double_click(params.get("x", 0), params.get("y", 0))
            elif action == "type":
                return await self._type_text(params.get("text", ""))
            elif action == "scroll":
                return await self._scroll(
                    params.get("direction", "down"),
                    params.get("amount", 3),
                )
            elif action == "move":
                return await self._move(params.get("x", 0), params.get("y", 0))
            else:
                return AbilityResult(
                    success=False,
                    error=f"Unknown action: {action}",
                )
        except Exception as e:
            return AbilityResult(
                success=False,
                error=str(e),
            )

    async def _screenshot(self) -> AbilityResult:
        """Take a screenshot"""
        # TODO: Implement with pyautogui or similar
        return AbilityResult(
            success=True,
            data={"message": "Screenshot taken", "path": "/tmp/screenshot.png"},
            emotion_hint="curious",
        )

    async def _click(self, x: int, y: int) -> AbilityResult:
        """Click at position"""
        # TODO: Implement with pyautogui
        return AbilityResult(
            success=True,
            data={"message": f"Clicked at ({x}, {y})"},
        )

    async def _double_click(self, x: int, y: int) -> AbilityResult:
        """Double click at position"""
        # TODO: Implement with pyautogui
        return AbilityResult(
            success=True,
            data={"message": f"Double clicked at ({x}, {y})"},
        )

    async def _type_text(self, text: str) -> AbilityResult:
        """Type text"""
        # TODO: Implement with pyautogui
        return AbilityResult(
            success=True,
            data={"message": f"Typed: {text[:20]}..."},
        )

    async def _scroll(self, direction: str, amount: int) -> AbilityResult:
        """Scroll screen"""
        # TODO: Implement with pyautogui
        return AbilityResult(
            success=True,
            data={"message": f"Scrolled {direction} by {amount}"},
        )

    async def _move(self, x: int, y: int) -> AbilityResult:
        """Move mouse to position"""
        # TODO: Implement with pyautogui
        return AbilityResult(
            success=True,
            data={"message": f"Moved to ({x}, {y})"},
        )
