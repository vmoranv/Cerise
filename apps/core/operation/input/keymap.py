"""
自定义按键映射

支持自定义按键配置，包括游戏专用按键、组合键映射等。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# 默认虚拟键码映射
DEFAULT_VK_CODES: dict[str, int] = {
    # 字母键
    **{chr(i): i for i in range(ord("A"), ord("Z") + 1)},
    **{chr(i).lower(): i for i in range(ord("A"), ord("Z") + 1)},
    # 数字键
    **{str(i): ord(str(i)) for i in range(10)},
    # 功能键
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    # 控制键
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "pause": 0x13,
    "capslock": 0x14,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "insert": 0x2D,
    "delete": 0x2E,
    # 修饰键
    "lshift": 0xA0,
    "rshift": 0xA1,
    "lctrl": 0xA2,
    "rctrl": 0xA3,
    "lalt": 0xA4,
    "ralt": 0xA5,
    # 小键盘
    "numpad0": 0x60,
    "numpad1": 0x61,
    "numpad2": 0x62,
    "numpad3": 0x63,
    "numpad4": 0x64,
    "numpad5": 0x65,
    "numpad6": 0x66,
    "numpad7": 0x67,
    "numpad8": 0x68,
    "numpad9": 0x69,
    "multiply": 0x6A,
    "add": 0x6B,
    "separator": 0x6C,
    "subtract": 0x6D,
    "decimal": 0x6E,
    "divide": 0x6F,
    # 符号键
    ";": 0xBA,
    "=": 0xBB,
    ",": 0xBC,
    "-": 0xBD,
    ".": 0xBE,
    "/": 0xBF,
    "`": 0xC0,
    "[": 0xDB,
    "\\": 0xDC,
    "]": 0xDD,
    "'": 0xDE,
}

# DirectInput 扫描码映射 (用于游戏)
DIK_CODES: dict[str, int] = {
    "escape": 0x01,
    "1": 0x02,
    "2": 0x03,
    "3": 0x04,
    "4": 0x05,
    "5": 0x06,
    "6": 0x07,
    "7": 0x08,
    "8": 0x09,
    "9": 0x0A,
    "0": 0x0B,
    "-": 0x0C,
    "=": 0x0D,
    "backspace": 0x0E,
    "tab": 0x0F,
    "q": 0x10,
    "w": 0x11,
    "e": 0x12,
    "r": 0x13,
    "t": 0x14,
    "y": 0x15,
    "u": 0x16,
    "i": 0x17,
    "o": 0x18,
    "p": 0x19,
    "[": 0x1A,
    "]": 0x1B,
    "enter": 0x1C,
    "lctrl": 0x1D,
    "a": 0x1E,
    "s": 0x1F,
    "d": 0x20,
    "f": 0x21,
    "g": 0x22,
    "h": 0x23,
    "j": 0x24,
    "k": 0x25,
    "l": 0x26,
    ";": 0x27,
    "'": 0x28,
    "`": 0x29,
    "lshift": 0x2A,
    "\\": 0x2B,
    "z": 0x2C,
    "x": 0x2D,
    "c": 0x2E,
    "v": 0x2F,
    "b": 0x30,
    "n": 0x31,
    "m": 0x32,
    ",": 0x33,
    ".": 0x34,
    "/": 0x35,
    "rshift": 0x36,
    "multiply": 0x37,
    "lalt": 0x38,
    "space": 0x39,
    "capslock": 0x3A,
    "f1": 0x3B,
    "f2": 0x3C,
    "f3": 0x3D,
    "f4": 0x3E,
    "f5": 0x3F,
    "f6": 0x40,
    "f7": 0x41,
    "f8": 0x42,
    "f9": 0x43,
    "f10": 0x44,
    "numlock": 0x45,
    "scrolllock": 0x46,
    "numpad7": 0x47,
    "numpad8": 0x48,
    "numpad9": 0x49,
    "subtract": 0x4A,
    "numpad4": 0x4B,
    "numpad5": 0x4C,
    "numpad6": 0x4D,
    "add": 0x4E,
    "numpad1": 0x4F,
    "numpad2": 0x50,
    "numpad3": 0x51,
    "numpad0": 0x52,
    "decimal": 0x53,
    "f11": 0x57,
    "f12": 0x58,
    "up": 0xC8,
    "left": 0xCB,
    "right": 0xCD,
    "down": 0xD0,
}


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
