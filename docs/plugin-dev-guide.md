# Cerise 插件开发完全指南

## 1. 架构总览

### 1.1 系统组件

Cerise 插件系统由以下核心组件构成：

- **Abilities 引擎** (`apps/core/abilities/`)
  - **AbilityRegistry**: 能力注册与管理
  - **BaseAbility**: 能力抽象基类
  - **PluginLoader**: 插件发现与加载

- **AI 核心** (`apps/core/ai/`)
  - **DialogueEngine**: 对话引擎，支持 Tool Calling
  - **EmotionAnalyzer**: 情感分析
  - **ProviderRegistry**: 多 Provider 管理

- **基础设施** (`apps/core/infrastructure/`)
  - **MessageBus**: 事件消息总线
  - **ConfigManager**: 配置管理
  - **StateStore**: 状态存储

### 1.2 数据流

```
用户输入 → API Gateway → DialogueEngine → AI Provider → Tool Calling → Abilities → 响应
```

### 1.3 插件生命周期

```
发现 → 加载 → 初始化 (on_load) → 运行 → 热重载 → 卸载 (on_unload)
```

---

## 2. 核心概念

### 2.1 Ability（能力）

Ability 是 Cerise 的核心扩展单元，分为：

| 类型 | 说明 | 位置 |
|------|------|------|
| **BUILTIN** | 内置能力 | `apps/core/abilities/builtin/` |
| **PLUGIN** | 外部插件 | `apps/core/abilities/plugins/` |

### 2.2 设计理念

- **类型安全**: 使用 Python 类型提示和 JSON Schema
- **异步优先**: 所有能力使用 `async/await`
- **工具调用**: 与 LLM Function Calling 无缝集成
- **热重载**: 支持运行时插件更新

---

## 3. 快速入门

### 3.1 创建简单插件

**目录结构：**
```
plugins/hello_world/
├── manifest.json      # 插件元数据
└── plugin.py          # 插件代码
```

**manifest.json:**
```json
{
  "name": "hello-world",
  "version": "1.0.0",
  "display_name": "Hello World",
  "description": "一个简单的示例插件",
  "author": "Your Name",
  "category": "utility",
  "entry_point": "plugin.py",
  "class_name": "HelloWorldPlugin",
  "permissions": [],
  "config_schema": {},
  "dependencies": {}
}
```

**plugin.py:**
```python
from apps.core.abilities import (
    BaseAbility,
    AbilityType,
    AbilityCategory,
    AbilityContext,
    AbilityResult,
)


class HelloWorldPlugin(BaseAbility):
    """Hello World 示例插件"""

    @property
    def name(self) -> str:
        return "hello_world"

    @property
    def display_name(self) -> str:
        return "Hello World"

    @property
    def description(self) -> str:
        return "打招呼，返回问候语"

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
                "name": {
                    "type": "string",
                    "description": "要问候的人名",
                }
            },
            "required": ["name"]
        }

    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        name = params["name"]
        return AbilityResult(
            success=True,
            data={"message": f"你好，{name}！"},
            emotion_hint="happy",  # 角色情感提示
        )
```

---

## 4. API 完整参考

### 4.1 BaseAbility (抽象基类)

```python
class BaseAbility(ABC):
    """能力抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """唯一标识符，用于 LLM Tool Calling"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """用户可见的显示名称"""

    @property
    @abstractmethod
    def description(self) -> str:
        """描述文本，提供给 LLM 理解能力功能"""

    @property
    @abstractmethod
    def ability_type(self) -> AbilityType:
        """BUILTIN 或 PLUGIN"""

    @property
    @abstractmethod
    def category(self) -> AbilityCategory:
        """能力分类：SYSTEM, MEDIA, NETWORK, CREATIVE, UTILITY, GAME"""

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """参数 JSON Schema，用于生成 OpenAI Tool Schema"""

    @property
    def required_permissions(self) -> list[str]:
        """所需权限列表"""
        return []

    @abstractmethod
    async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
        """执行能力"""

    async def validate_params(self, params: dict) -> bool:
        """参数校验（可选）"""
        return True

    async def on_load(self) -> None:
        """插件加载回调"""

    async def on_unload(self) -> None:
        """插件卸载回调"""

    def to_tool_schema(self) -> dict:
        """转换为 OpenAI Tool Schema"""
```

### 4.2 AbilityContext (执行上下文)

```python
@dataclass
class AbilityContext:
    """能力执行上下文"""
    user_id: str           # 用户 ID
    session_id: str        # 会话 ID
    character_state: dict  # 角色状态（情感等）
    permissions: list[str] # 已授权的权限
```

### 4.3 AbilityResult (执行结果)

```python
@dataclass
class AbilityResult:
    """能力执行结果"""
    success: bool                    # 是否成功
    data: Any = None                 # 返回数据
    error: str | None = None         # 错误信息
    emotion_hint: str | None = None  # 情感提示（影响角色表情）
```

### 4.4 AbilityRegistry (注册表)

```python
class AbilityRegistry:
    """能力注册与管理"""

    @classmethod
    def register(cls, ability: BaseAbility) -> None:
        """注册能力实例"""

    @classmethod
    def get(cls, name: str) -> BaseAbility | None:
        """获取能力"""

    @classmethod
    def list_abilities(cls) -> list[str]:
        """列出所有能力名称"""

    @classmethod
    async def execute(cls, name: str, params: dict, context: AbilityContext) -> AbilityResult:
        """执行能力"""

    @classmethod
    async def load_plugins(cls, plugins_dir: str | Path) -> None:
        """加载插件目录"""

    @classmethod
    def get_tool_schemas(cls) -> list[dict]:
        """获取所有 OpenAI Tool Schema"""
```

---

## 5. Manifest 规范

### 5.1 必需字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 插件唯一标识（小写+连字符） |
| `version` | string | 语义化版本号 |
| `display_name` | string | 显示名称 |
| `description` | string | 插件描述 |
| `author` | string | 作者名 |
| `category` | string | 分类：system/media/network/creative/utility/game |
| `entry_point` | string | 入口文件 |
| `class_name` | string | 主类名 |

### 5.2 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `permissions` | array | 所需权限列表 |
| `config_schema` | object | 配置项 JSON Schema |
| `dependencies` | object | Python 依赖 |
| `cerise_version` | string | 兼容的 Cerise 版本 |

### 5.3 完整示例

```json
{
  "$schema": "https://cerise.dev/schemas/plugin-manifest.json",
  "name": "pixiv-search",
  "version": "1.0.0",
  "display_name": "Pixiv 搜索",
  "description": "搜索 Pixiv 上的插画作品并展示",
  "author": "Cerise Team",
  "category": "creative",
  "entry_point": "plugin.py",
  "class_name": "PixivSearchPlugin",
  "permissions": [
    "network.http",
    "storage.cache"
  ],
  "config_schema": {
    "type": "object",
    "properties": {
      "refresh_token": {
        "type": "string",
        "description": "Pixiv Refresh Token",
        "secret": true
      },
      "nsfw_filter": {
        "type": "boolean",
        "default": true,
        "description": "过滤 NSFW 内容"
      },
      "max_results": {
        "type": "integer",
        "default": 5,
        "minimum": 1,
        "maximum": 20
      }
    },
    "required": ["refresh_token"]
  },
  "dependencies": {
    "pixivpy3": ">=3.7.0",
    "aiohttp": ">=3.9.0"
  },
  "cerise_version": ">=0.1.0"
}
```

---

## 6. 权限系统

### 6.1 权限列表

| 权限 | 说明 | 风险级别 |
|------|------|---------|
| `system.execute` | 执行代码 | 🔴 高 |
| `system.computer_use` | 控制电脑 | 🔴 高 |
| `system.file_read` | 读取文件 | 🟡 中 |
| `system.file_write` | 写入文件 | 🟡 中 |
| `network.http` | HTTP 请求 | 🟡 中 |
| `network.websocket` | WebSocket | 🟡 中 |
| `storage.cache` | 缓存访问 | 🟢 低 |
| `storage.database` | 数据库访问 | 🟡 中 |

### 6.2 权限检查

```python
# 在 execute 中自动检查
async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
    # AbilityRegistry 会自动检查 required_permissions
    # 如果权限不足，会返回错误
    ...
```

---

## 7. 高级功能

### 7.1 配置访问

```python
class MyPlugin(BaseAbility):
    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
        api_key = self.config.get("api_key")
        ...
```

### 7.2 状态存储

```python
from apps.core.infrastructure import StateStore

class MyPlugin(BaseAbility):
    def __init__(self):
        self.store = StateStore()

    async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
        # 读取状态
        count = await self.store.get(f"plugin.myPlugin.{context.user_id}.count", 0)
        
        # 更新状态
        await self.store.set(f"plugin.myPlugin.{context.user_id}.count", count + 1)
        ...
```

### 7.3 事件发布

```python
from apps.core.infrastructure import MessageBus, Event

class MyPlugin(BaseAbility):
    def __init__(self):
        self.bus = MessageBus()

    async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
        # 发布事件
        await self.bus.emit(
            "plugin.myPlugin.action",
            {"action": "search", "user_id": context.user_id},
            source="my_plugin",
        )
        ...
```

### 7.4 情感影响

```python
async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
    return AbilityResult(
        success=True,
        data={"result": "..."},
        emotion_hint="excited",  # 可选值: happy, sad, excited, curious, confused...
    )
```

---

## 8. 最佳实践

### 8.1 代码组织

```
plugins/my_plugin/
├── manifest.json       # 元数据
├── plugin.py           # 主入口
├── utils/              # 工具函数
│   └── helpers.py
├── requirements.txt    # 依赖（可选）
└── README.md           # 文档
```

### 8.2 错误处理

```python
async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
    try:
        result = await self._do_something(params)
        return AbilityResult(success=True, data=result)
    except ValueError as e:
        return AbilityResult(success=False, error=f"参数错误: {e}")
    except Exception as e:
        logger.exception("Unexpected error")
        return AbilityResult(success=False, error="内部错误，请稍后重试")
```

### 8.3 异步编程

```python
import asyncio
import aiohttp

async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
    # ✅ 使用异步 HTTP
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

    # ✅ 并发请求
    results = await asyncio.gather(
        self._fetch_data_1(),
        self._fetch_data_2(),
    )
```

### 8.4 资源管理

```python
async def on_load(self) -> None:
    """初始化资源"""
    self.client = await create_client()

async def on_unload(self) -> None:
    """清理资源"""
    if self.client:
        await self.client.close()
```

---

## 9. 示例插件

### 9.1 Pixiv 搜索插件

```python
from apps.core.abilities import (
    BaseAbility, AbilityType, AbilityCategory,
    AbilityContext, AbilityResult,
)


class PixivSearchPlugin(BaseAbility):
    """Pixiv 插画搜索插件"""

    name = "pixiv_search"
    display_name = "Pixiv 搜索"
    description = "搜索 Pixiv 上的插画作品"
    ability_type = AbilityType.PLUGIN
    category = AbilityCategory.CREATIVE

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "count": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "返回数量",
                },
            },
            "required": ["keyword"],
        }

    required_permissions = ["network.http"]

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.client = None

    async def on_load(self) -> None:
        from pixivpy3 import AppPixivAPI
        self.client = AppPixivAPI()
        refresh_token = self.config.get("refresh_token")
        if refresh_token:
            self.client.auth(refresh_token=refresh_token)

    async def on_unload(self) -> None:
        self.client = None

    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        if not self.client:
            return AbilityResult(
                success=False,
                error="Pixiv 客户端未初始化",
            )

        keyword = params["keyword"]
        count = params.get("count", 5)

        try:
            result = self.client.search_illust(keyword)
            illusts = result.illusts[:count]

            return AbilityResult(
                success=True,
                data={
                    "keyword": keyword,
                    "count": len(illusts),
                    "illustrations": [
                        {
                            "id": i.id,
                            "title": i.title,
                            "author": i.user.name,
                            "url": i.image_urls.medium,
                        }
                        for i in illusts
                    ],
                },
                emotion_hint="excited",
            )
        except Exception as e:
            return AbilityResult(
                success=False,
                error=str(e),
            )
```

---

## 10. 故障排查

### 10.1 常见问题

| 问题 | 解决方案 |
|------|---------|
| 插件无法加载 | 检查 manifest.json 格式和 class_name |
| 权限不足 | 在 manifest 中声明 permissions |
| 参数校验失败 | 检查 parameters_schema 定义 |
| 依赖缺失 | 在 dependencies 中声明或手动安装 |

### 10.2 调试

```python
import logging

logger = logging.getLogger(__name__)

async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
    logger.debug(f"Params: {params}")
    logger.info(f"Executing with context: {context.session_id}")
    ...
```

---

## 11. 附录

### 11.1 类型定义

```python
from enum import Enum

class AbilityType(Enum):
    BUILTIN = "builtin"
    PLUGIN = "plugin"

class AbilityCategory(Enum):
    SYSTEM = "system"
    MEDIA = "media"
    NETWORK = "network"
    CREATIVE = "creative"
    UTILITY = "utility"
    GAME = "game"
```

### 11.2 情感提示值

| 值 | 说明 |
|---|------|
| `happy` | 开心 |
| `sad` | 悲伤 |
| `excited` | 兴奋 |
| `curious` | 好奇 |
| `confused` | 困惑 |
| `satisfied` | 满足 |
| `concerned` | 担忧 |
| `shy` | 害羞 |
