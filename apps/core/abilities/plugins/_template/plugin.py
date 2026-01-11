"""
Example Plugin Template

Copy this template to create your own plugin.
"""

from apps.core.abilities.base import (
    AbilityCategory,
    AbilityContext,
    AbilityResult,
    AbilityType,
    BaseAbility,
)


class ExamplePlugin(BaseAbility):
    """Example plugin template"""

    @property
    def name(self) -> str:
        return "example_plugin"

    @property
    def display_name(self) -> str:
        return "示例插件"

    @property
    def description(self) -> str:
        return "这是一个示例插件，展示如何创建自定义能力"

    @property
    def ability_type(self) -> AbilityType:
        return AbilityType.PLUGIN

    @property
    def category(self) -> AbilityCategory:
        return AbilityCategory.UTILITY

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "输入参数",
                },
            },
            "required": ["input"],
        }

    @property
    def required_permissions(self) -> list[str]:
        return []

    async def on_load(self) -> None:
        """Called when plugin is loaded"""
        print(f"Plugin {self.name} loaded!")

    async def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        print(f"Plugin {self.name} unloaded!")

    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute the plugin"""
        input_text = params["input"]

        # Your plugin logic here
        result = f"处理结果: {input_text}"

        return AbilityResult(
            success=True,
            data={"result": result},
            emotion_hint="happy",
        )
