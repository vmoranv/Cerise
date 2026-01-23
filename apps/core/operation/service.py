"""
操作层主服务

提供统一的游戏/应用自动化操作接口。
"""

from __future__ import annotations

import time
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING

import numpy as np
from apps.core.contracts.events import (
    OPERATION_ACTION_COMPLETED,
    OPERATION_INPUT_PERFORMED,
    OPERATION_TEMPLATE_MATCHED,
    OPERATION_WINDOW_CONNECTED,
    OPERATION_WINDOW_DISCONNECTED,
    build_operation_action_completed,
    build_operation_input_performed,
    build_operation_template_matched,
    build_operation_window_connected,
    build_operation_window_disconnected,
)
from apps.core.infrastructure import Event, EventBus

from operation.capture.base import CaptureMethod
from operation.capture.win32_bitblt import Win32BitBltCapture
from operation.input.base import Interaction
from operation.input.win32 import Win32Interaction
from operation.vision.box import Box
from operation.vision.template import (
    find_color,
    load_template,
    match_template,
    match_template_all,
)
from operation.window import (
    WindowInfo,
    bring_to_front,
    find_window_by_title,
    find_windows,
    get_window_info,
)

if TYPE_CHECKING:
    from operation.workflow.actions import Action
    from operation.workflow.types import ActionResult


class OperationService:
    """操作层主服务

    整合屏幕捕获、输入模拟、视觉分析功能，提供统一的自动化操作接口。

    Example:
        >>> service = OperationService()
        >>> service.connect_by_title("游戏窗口")
        >>> frame = service.get_frame()
        >>> box = service.find_template("button.png")
        >>> if box:
        ...     service.click_box(box)
    """

    def __init__(
        self,
        capture: CaptureMethod | None = None,
        interaction: Interaction | None = None,
        bus: EventBus | None = None,
    ) -> None:
        """初始化操作服务

        Args:
            capture: 屏幕捕获实现，默认使用 Win32BitBlt
            interaction: 输入模拟实现，默认使用 Win32Interaction
            bus: 事件总线，用于发布操作层事件
        """
        self._capture = capture or Win32BitBltCapture()
        self._interaction = interaction or Win32Interaction()
        self._bus = bus

    def _publish_event(self, event_type: str, data: dict[str, object]) -> None:
        if not self._bus:
            return
        self._bus.publish_sync(Event(type=event_type, data=data, source="operation_service"))

    @staticmethod
    def _box_payload(box: Box) -> dict[str, object]:
        return {
            "x": box.x,
            "y": box.y,
            "width": box.width,
            "height": box.height,
            "confidence": box.confidence,
            "name": box.name,
        }

    def _normalize_action_data(self, data: object | None) -> dict[str, object] | None:
        if data is None:
            return None
        if isinstance(data, Box):
            return self._box_payload(data)
        if isinstance(data, dict):
            return data
        return {"value": data}

    def emit_action_result(self, action: Action, result: ActionResult) -> None:
        if not self._bus:
            return
        data_payload = self._normalize_action_data(result.data)
        self._publish_event(
            OPERATION_ACTION_COMPLETED,
            build_operation_action_completed(
                action=action.name,
                action_type=action.__class__.__name__,
                status=result.status.name.lower(),
                message=result.message,
                duration=result.duration,
                data=data_payload,
            ),
        )
        self._hwnd: int = 0
        self._template_cache: dict[str, np.ndarray] = {}
        self._template_dir: Path | None = None

    @property
    def hwnd(self) -> int:
        """当前绑定的窗口句柄"""
        return self._hwnd

    @property
    def width(self) -> int:
        """窗口客户区宽度"""
        return self._capture.width

    @property
    def height(self) -> int:
        """窗口客户区高度"""
        return self._capture.height

    @property
    def capture(self) -> CaptureMethod:
        """屏幕捕获实例"""
        return self._capture

    @property
    def interaction(self) -> Interaction:
        """输入模拟实例"""
        return self._interaction

    def set_template_dir(self, path: str | Path) -> None:
        """设置模板图像目录

        Args:
            path: 模板目录路径
        """
        self._template_dir = Path(path)

    # ========== 窗口管理 ==========

    def connect(self, hwnd: int) -> bool:
        """连接到目标窗口

        Args:
            hwnd: 窗口句柄

        Returns:
            连接是否成功
        """
        if not self._capture.connect(hwnd):
            return False
        if not self._interaction.connect(hwnd):
            self._capture.close()
            return False
        self._hwnd = hwnd
        self._publish_event(
            OPERATION_WINDOW_CONNECTED,
            build_operation_window_connected(self._hwnd, self._capture.width, self._capture.height),
        )
        return True

    def connect_by_title(
        self,
        title: str | Pattern[str],
        exact: bool = False,
    ) -> bool:
        """根据标题连接到窗口

        Args:
            title: 窗口标题（支持正则表达式）
            exact: 是否精确匹配

        Returns:
            连接是否成功
        """
        hwnd = find_window_by_title(title, exact=exact)
        if hwnd is None:
            return False
        return self.connect(hwnd)

    def connected(self) -> bool:
        """检查是否已连接"""
        return self._hwnd != 0 and self._capture.connected() and self._interaction.connected()

    def get_window_info(self) -> WindowInfo | None:
        """获取当前窗口信息"""
        if self._hwnd == 0:
            return None
        return get_window_info(self._hwnd)

    def bring_to_front(self) -> bool:
        """将窗口置于前台"""
        if self._hwnd == 0:
            return False
        return bring_to_front(self._hwnd)

    def list_windows(
        self,
        title: str | Pattern[str] | None = None,
        class_name: str | Pattern[str] | None = None,
    ) -> list[WindowInfo]:
        """列出符合条件的窗口"""
        return find_windows(title=title, class_name=class_name)

    # ========== 屏幕捕获 ==========

    def get_frame(self) -> np.ndarray | None:
        """获取当前帧

        Returns:
            BGR 格式的图像数组，失败返回 None
        """
        return self._capture.get_frame()

    def get_frame_region(self, box: Box) -> np.ndarray | None:
        """获取指定区域的帧

        Args:
            box: 目标区域

        Returns:
            裁剪后的图像，失败返回 None
        """
        frame = self.get_frame()
        if frame is None:
            return None
        return box.crop_frame(frame)

    # ========== 模板匹配 ==========

    def _get_template(self, template: str | np.ndarray) -> np.ndarray | None:
        """获取模板图像（支持缓存）"""
        if isinstance(template, np.ndarray):
            return template

        # 检查缓存
        if template in self._template_cache:
            return self._template_cache[template]

        # 加载模板
        path = Path(template)
        if not path.is_absolute() and self._template_dir is not None:
            path = self._template_dir / template

        template_img = load_template(path)
        if template_img is not None:
            self._template_cache[template] = template_img
        return template_img

    def find_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        frame: np.ndarray | None = None,
        region: Box | None = None,
        name: str | None = None,
    ) -> Box | None:
        """查找模板

        Args:
            template: 模板图像或路径
            threshold: 匹配阈值
            frame: 源图像（默认获取当前帧）
            region: 搜索区域（可选）
            name: 返回的 Box 名称

        Returns:
            匹配到的 Box，未找到返回 None
        """
        template_img = self._get_template(template)
        if template_img is None:
            return None

        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return None

        # 如果指定了搜索区域
        offset_x, offset_y = 0, 0
        if region is not None:
            frame = region.crop_frame(frame)
            offset_x, offset_y = region.x, region.y

        result = match_template(frame, template_img, threshold=threshold, name=name)

        # 调整坐标偏移
        if result is not None and (offset_x != 0 or offset_y != 0):
            result = result.copy(x_offset=offset_x, y_offset=offset_y)

        if result is not None:
            template_name = template if isinstance(template, str) else "<array>"
            self._publish_event(
                OPERATION_TEMPLATE_MATCHED,
                build_operation_template_matched(
                    template=template_name,
                    threshold=threshold,
                    box=self._box_payload(result),
                ),
            )

        return result

    def find_all_templates(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        frame: np.ndarray | None = None,
        region: Box | None = None,
        name: str | None = None,
        max_results: int = 100,
    ) -> list[Box]:
        """查找所有模板匹配

        Args:
            template: 模板图像或路径
            threshold: 匹配阈值
            frame: 源图像（默认获取当前帧）
            region: 搜索区域（可选）
            name: 返回的 Box 名称
            max_results: 最大返回数量

        Returns:
            匹配到的 Box 列表
        """
        template_img = self._get_template(template)
        if template_img is None:
            return []

        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return []

        offset_x, offset_y = 0, 0
        if region is not None:
            frame = region.crop_frame(frame)
            offset_x, offset_y = region.x, region.y

        results = match_template_all(frame, template_img, threshold=threshold, name=name, max_results=max_results)

        # 调整坐标偏移
        if offset_x != 0 or offset_y != 0:
            results = [box.copy(x_offset=offset_x, y_offset=offset_y) for box in results]

        return results

    def wait_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        timeout: float = 10.0,
        interval: float = 0.1,
        region: Box | None = None,
        name: str | None = None,
    ) -> Box | None:
        """等待模板出现

        Args:
            template: 模板图像或路径
            threshold: 匹配阈值
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
            region: 搜索区域（可选）
            name: 返回的 Box 名称

        Returns:
            匹配到的 Box，超时返回 None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.find_template(template, threshold=threshold, region=region, name=name)
            if result is not None:
                return result
            time.sleep(interval)
        return None

    def find_color(
        self,
        color_lower: tuple[int, int, int],
        color_upper: tuple[int, int, int],
        color_space: str = "BGR",
        min_area: int = 10,
        frame: np.ndarray | None = None,
        region: Box | None = None,
    ) -> list[Box]:
        """颜色查找

        Args:
            color_lower: 颜色下界
            color_upper: 颜色上界
            color_space: 颜色空间 ('BGR' 或 'HSV')
            min_area: 最小区域面积
            frame: 源图像（默认获取当前帧）
            region: 搜索区域（可选）

        Returns:
            匹配的区域列表
        """
        if frame is None:
            frame = self.get_frame()
        if frame is None:
            return []

        offset_x, offset_y = 0, 0
        if region is not None:
            frame = region.crop_frame(frame)
            offset_x, offset_y = region.x, region.y

        results = find_color(frame, color_lower, color_upper, color_space, min_area)

        if offset_x != 0 or offset_y != 0:
            results = [box.copy(x_offset=offset_x, y_offset=offset_y) for box in results]

        return results

    # ========== 输入操作 ==========

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
    ) -> None:
        """点击指定位置"""
        self._interaction.click(x, y, button)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="click",
                hwnd=self._hwnd,
                params={"x": x, "y": y, "button": button},
            ),
        )

    def click_box(
        self,
        box: Box,
        button: str = "left",
        relative_x: float = 0.5,
        relative_y: float = 0.5,
    ) -> None:
        """点击 Box 区域"""
        self._interaction.click_box(box, button, relative_x, relative_y)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="click_box",
                hwnd=self._hwnd,
                params={
                    "box": self._box_payload(box),
                    "button": button,
                    "relative_x": relative_x,
                    "relative_y": relative_y,
                },
            ),
        )

    def double_click(
        self,
        x: int,
        y: int,
        button: str = "left",
    ) -> None:
        """双击指定位置"""
        self._interaction.double_click(x, y, button)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="double_click",
                hwnd=self._hwnd,
                params={"x": x, "y": y, "button": button},
            ),
        )

    def move(self, x: int, y: int) -> None:
        """移动鼠标"""
        self._interaction.move(x, y)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="move",
                hwnd=self._hwnd,
                params={"x": x, "y": y},
            ),
        )

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        button: str = "left",
        duration: float = 0.0,
    ) -> None:
        """拖拽操作"""
        self._interaction.drag(from_x, from_y, to_x, to_y, button, duration)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="drag",
                hwnd=self._hwnd,
                params={
                    "from_x": from_x,
                    "from_y": from_y,
                    "to_x": to_x,
                    "to_y": to_y,
                    "button": button,
                    "duration": duration,
                },
            ),
        )

    def scroll(self, x: int, y: int, delta: int) -> None:
        """滚动鼠标滚轮"""
        self._interaction.scroll(x, y, delta)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="scroll",
                hwnd=self._hwnd,
                params={"x": x, "y": y, "delta": delta},
            ),
        )

    def key_press(self, key: str, duration: float = 0.0) -> None:
        """按下并释放按键"""
        self._interaction.key_press(key, duration)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="key_press",
                hwnd=self._hwnd,
                params={"key": key, "duration": duration},
            ),
        )

    def key_down(self, key: str) -> None:
        """按下键盘按键"""
        self._interaction.key_down(key)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="key_down",
                hwnd=self._hwnd,
                params={"key": key},
            ),
        )

    def key_up(self, key: str) -> None:
        """释放键盘按键"""
        self._interaction.key_up(key)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="key_up",
                hwnd=self._hwnd,
                params={"key": key},
            ),
        )

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """输入文本"""
        self._interaction.type_text(text, interval)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="type_text",
                hwnd=self._hwnd,
                params={"text": text, "interval": interval},
            ),
        )

    def hotkey(self, *keys: str) -> None:
        """执行组合键"""
        self._interaction.hotkey(*keys)
        self._publish_event(
            OPERATION_INPUT_PERFORMED,
            build_operation_input_performed(
                action="hotkey",
                hwnd=self._hwnd,
                params={"keys": list(keys)},
            ),
        )

    # ========== 便捷操作 ==========

    def click_template(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        button: str = "left",
        timeout: float = 0.0,
        region: Box | None = None,
    ) -> bool:
        """查找并点击模板

        Args:
            template: 模板图像或路径
            threshold: 匹配阈值
            button: 鼠标按键
            timeout: 等待超时（0 表示不等待）
            region: 搜索区域（可选）

        Returns:
            是否成功点击
        """
        if timeout > 0:
            box = self.wait_template(template, threshold, timeout, region=region)
        else:
            box = self.find_template(template, threshold, region=region)

        if box is None:
            return False

        self.click_box(box, button)
        return True

    def wait_and_click(
        self,
        template: str | np.ndarray,
        threshold: float = 0.8,
        timeout: float = 10.0,
        button: str = "left",
    ) -> bool:
        """等待模板出现并点击

        Args:
            template: 模板图像或路径
            threshold: 匹配阈值
            timeout: 超时时间
            button: 鼠标按键

        Returns:
            是否成功点击
        """
        return self.click_template(template, threshold, button, timeout)

    # ========== 资源管理 ==========

    def clear_template_cache(self) -> None:
        """清空模板缓存"""
        self._template_cache.clear()

    def close(self) -> None:
        """释放资源"""
        if self._hwnd:
            self._publish_event(
                OPERATION_WINDOW_DISCONNECTED,
                build_operation_window_disconnected(self._hwnd),
            )
        self._capture.close()
        self._interaction.close()
        self._hwnd = 0
        self._template_cache.clear()

    def __enter__(self) -> OperationService:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
