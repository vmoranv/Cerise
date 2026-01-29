"""
自定义按键映射

支持自定义按键配置，包括游戏专用按键、组合键映射等。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .keymap_codes import DEFAULT_VK_CODES, DIK_CODES


@dataclass
class KeyBinding:
    """按键绑定"""

    name: str  # 逻辑名称 (如 "attack", "jump")
    key: str  # 实际按键 (如 "space", "j")
    modifiers: list[str] = field(default_factory=list)  # 修饰键
    hold_time: float = 0.0  # 按住时间
    description: str = ""


@dataclass
class KeyMap:
    """按键映射配置

    支持游戏自定义按键配置。

    Example:
        >>> keymap = KeyMap()
        >>> keymap.bind("attack", "j")
        >>> keymap.bind("jump", "space")
        >>> keymap.bind("skill1", "1", modifiers=["shift"])
        >>>
        >>> # 获取按键
        >>> key = keymap.get("attack")  # "j"
    """

    bindings: dict[str, KeyBinding] = field(default_factory=dict)
    vk_codes: dict[str, int] = field(default_factory=lambda: DEFAULT_VK_CODES.copy())
    use_directinput: bool = False

    def bind(
        self,
        name: str,
        key: str,
        modifiers: list[str] | None = None,
        hold_time: float = 0.0,
        description: str = "",
    ) -> None:
        """绑定按键

        Args:
            name: 逻辑名称
            key: 实际按键
            modifiers: 修饰键列表
            hold_time: 按住时间
            description: 描述
        """
        self.bindings[name] = KeyBinding(
            name=name,
            key=key.lower(),
            modifiers=[m.lower() for m in (modifiers or [])],
            hold_time=hold_time,
            description=description,
        )

    def unbind(self, name: str) -> None:
        """解除绑定"""
        self.bindings.pop(name, None)

    def get(self, name: str) -> str | None:
        """获取绑定的按键"""
        binding = self.bindings.get(name)
        return binding.key if binding else None

    def get_binding(self, name: str) -> KeyBinding | None:
        """获取完整绑定信息"""
        return self.bindings.get(name)

    def get_vk(self, key: str) -> int:
        """获取虚拟键码"""
        key = key.lower()
        if self.use_directinput:
            return DIK_CODES.get(key, 0)
        return self.vk_codes.get(key, 0)

    def add_custom_key(self, name: str, vk_code: int) -> None:
        """添加自定义按键码"""
        self.vk_codes[name.lower()] = vk_code

    def save(self, path: str | Path) -> None:
        """保存配置到文件"""
        data = {
            "bindings": {
                name: {
                    "key": b.key,
                    "modifiers": b.modifiers,
                    "hold_time": b.hold_time,
                    "description": b.description,
                }
                for name, b in self.bindings.items()
            },
            "custom_keys": {k: v for k, v in self.vk_codes.items() if k not in DEFAULT_VK_CODES},
            "use_directinput": self.use_directinput,
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: str | Path) -> KeyMap:
        """从文件加载配置"""
        path = Path(path)
        if not path.exists():
            return cls()

        data = json.loads(path.read_text())
        keymap = cls(use_directinput=data.get("use_directinput", False))

        # 加载自定义键码
        for name, vk in data.get("custom_keys", {}).items():
            keymap.add_custom_key(name, vk)

        # 加载绑定
        for name, binding in data.get("bindings", {}).items():
            keymap.bind(
                name=name,
                key=binding["key"],
                modifiers=binding.get("modifiers", []),
                hold_time=binding.get("hold_time", 0.0),
                description=binding.get("description", ""),
            )

        return keymap


# 预设游戏按键配置
def create_wasd_preset() -> KeyMap:
    """创建 WASD 移动预设"""
    keymap = KeyMap()
    keymap.bind("move_up", "w", description="向上移动")
    keymap.bind("move_down", "s", description="向下移动")
    keymap.bind("move_left", "a", description="向左移动")
    keymap.bind("move_right", "d", description="向右移动")
    keymap.bind("jump", "space", description="跳跃")
    keymap.bind("crouch", "ctrl", description="蹲下")
    keymap.bind("sprint", "shift", description="冲刺")
    return keymap


def create_arrow_preset() -> KeyMap:
    """创建方向键移动预设"""
    keymap = KeyMap()
    keymap.bind("move_up", "up", description="向上移动")
    keymap.bind("move_down", "down", description="向下移动")
    keymap.bind("move_left", "left", description="向左移动")
    keymap.bind("move_right", "right", description="向右移动")
    keymap.bind("action1", "z", description="动作1")
    keymap.bind("action2", "x", description="动作2")
    keymap.bind("action3", "c", description="动作3")
    return keymap
