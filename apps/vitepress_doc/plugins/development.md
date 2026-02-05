# 插件开发指南

Cerise Core 的插件系统是一个“可被 LLM 调用的工具层”。插件以独立进程（stdio）或独立服务（HTTP）运行，通过 **JSON-RPC 2.0** 与 Core 通信，并向 Core 暴露一组 **abilities/tools**。

本页面面向插件作者，覆盖：目录结构、`manifest.json`、协议、配置/权限、安全边界、依赖安装、多语言 SDK 与调试建议。

---

## 1. 你要实现什么

一个插件 = 一个目录 + 一个 `manifest.json` + 一个可执行入口：

- Core 启动插件进程
- Core 发送 `initialize`
- 插件返回它提供的 abilities
- LLM 调用时，Core 发送 `execute`
- 插件返回 `{ success, data|error, emotion_hint }`

---

## 2. 插件目录结构

推荐结构（以 Python 为例）：

```
my-plugin/
  manifest.json
  main.py
  requirements.txt        # 可选：Python 依赖
  _conf_schema.json        # 可选：Star Config 配置 schema（推荐）
  README.md                # 可选
```

注意：

- 插件目录名通常等于 `manifest.json` 里的 `name`（安装时会按 `name` 创建目录）。
- `name` **必须是安全的短名**（建议 kebab-case），不能包含 `/`、`\\`、`:`。

---

## 3. manifest.json 规范

Core 读取 `manifest.json` 来决定如何启动插件，以及给 Admin/API/UI 提供元信息。

示例（stdio + Node.js）：

```json
{
  "name": "web-search",
  "version": "1.0.0",
  "display_name": "网页搜索",
  "description": "搜索网页内容",
  "author": "Cerise Team",
  "runtime": {
    "language": "nodejs",
    "entry": "index.js",
    "command": "node index.js",
    "transport": "stdio"
  },
  "abilities": [
    {
      "name": "web_search",
      "description": "搜索网页内容",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "搜索查询"},
          "count": {"type": "integer", "default": 5, "description": "返回数量"}
        },
        "required": ["query"]
      }
    }
  ],
  "permissions": ["network.http"],
  "config_schema": {
    "type": "object",
    "properties": {
      "api_key": {"type": "string", "description": "Search API Key", "secret": true}
    }
  }
}
```

字段说明（常用）：

- `name`：插件唯一标识（**安全短名**，建议 `kebab-case`）。
- `version`：语义化版本。
- `display_name` / `description` / `author`：展示信息。
- `runtime`：运行时信息
  - `transport`：`"stdio"` 或 `"http"`
  - `language`：`python` / `nodejs` / `go` / `binary` / `cpp` 等（用于默认启动命令推断）
  - `entry`：入口文件/可执行文件
  - `command`：显式命令（优先级最高；stdio 下用 `create_subprocess_shell` 执行）
  - `http_url`：HTTP transport 时必须提供（Core 会 POST 到 `${http_url}/rpc`）
- `abilities`：插件静态声明的 abilities 列表（initialize 也可以返回动态 abilities；Core 会优先使用 initialize 返回结果）。
- `permissions`：插件声明“它希望拥有的能力/权限”（会在 initialize 时传给插件）。
- `config_schema`：插件配置的 schema（主要给 UI/文档使用；Core 的 Star Config schema **实际读取的是** `_conf_schema.json`，见后文）。

---

## 4. Ability（Tool）定义

`abilities[]` 每一项建议包含：

- `name`：工具名（建议 `snake_case`，并避免与其他插件冲突，可用前缀如 `web_search` / `github_issue_create`）
- `description`：给 LLM 的自然语言描述
- `parameters`：JSON Schema（OpenAI function-calling 风格）

兼容性：Core 会把 `inputSchema` / `input_schema` 自动归一为 `parameters`。

---

## 5. JSON-RPC 协议（stdio / HTTP）

### 5.1 数据格式

- **一行一个 JSON**（newline-delimited JSON）
- 请求：`{ "jsonrpc": "2.0", "method": "...", "params": { ... }, "id": 1 }`
- 响应：`{ "jsonrpc": "2.0", "result": { ... }, "id": 1 }` 或 `error`

重要：

- **stdout 只能输出协议 JSON**；日志请写到 **stderr**，否则会破坏通信。

### 5.2 initialize

Core -> Plugin：

```json
{"jsonrpc":"2.0","method":"initialize","params":{"plugin_name":"web-search","config":{},"permissions":["network.http"]},"id":1}
```

Plugin -> Core：

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "abilities": [
      {"name": "web_search", "description": "...", "parameters": {"type":"object","properties":{},"required":[]}}
    ]
  },
  "id": 1
}
```

兼容字段：Core 会按顺序尝试从 `result.abilities` / `result.skills` / `result.tools` / `result.mcp.tools` 读取 abilities。

### 5.3 execute

Core -> Plugin：

```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "ability": "web_search",
    "params": {"query": "cerise", "count": 3},
    "context": {"user_id": "u1", "session_id": "s1", "permissions": ["network.http"]}
  },
  "id": 2
}
```

Plugin -> Core：

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "data": {"results": []},
    "error": null,
    "emotion_hint": "satisfied"
  },
  "id": 2
}
```

### 5.4 health / shutdown

- `health`：返回 `{ "healthy": true }`
- `shutdown`：插件做清理后返回 `{ "success": true }` 并退出

---

## 6. 配置（Star Config）与 `_conf_schema.json`

插件通常需要可配置项（API Key、开关、阈值等）。Core 的推荐做法是使用 **Star Config**：

- schema：放在插件目录 `/_conf_schema.json`
- 实际配置：由 Core 存在数据目录 `stars/*_config.json`，并在 `initialize` 时通过 `params.config` 传给插件

Admin API（需要 /admin 鉴权）：

- `GET /admin/stars/{name}/schema`
- `GET /admin/stars/{name}/config`
- `PUT /admin/stars/{name}/config`（合并更新，并按 schema 验证/补默认值）

最小 `_conf_schema.json` 示例：

```json
{
  "type": "object",
  "properties": {
    "api_key": {"type": "string", "title": "API Key"},
    "base_url": {"type": "string", "default": "https://api.example.com"}
  },
  "required": ["api_key"]
}
```

---

## 7. 权限与安全边界（必须读）

Cerise Core 有两层“能否被调用”的控制：

1) **CapabilityScheduler**：决定某个 ability 是否对 LLM “可见/可用”（受 `capabilities.*` 与 Star registry 的 `enabled/allow_tools` 影响）。
2) **AbilityContext.permissions**：执行时传入的权限列表，插件应当自行检查。

建议规则：

- 把危险行为（执行命令、访问本机敏感文件、发网、写磁盘）都做成显式能力，并在插件内部要求特定权限。
- 插件不要相信来自 LLM 的任何参数（做白名单校验、长度限制、URL 校验等）。
- `stdout` 只输出协议；日志用 `stderr`。

::: tip
Core 默认 `tools.permissions = []`，因此即使 ability 存在，也可以通过权限控制让它“默认不能做危险事”。
:::

---

## 8. 依赖安装（可选）

Core 支持“可选的依赖安装”，用于降低用户手动配置成本。

- 配置项：`plugins.auto_install_dependencies`（默认 false）
- Python venv 目录：`plugins.python_venv_dir`（默认 `.venv`，位于插件目录内）

行为：

- Python：优先 `requirements.txt`；否则读 `manifest.json` 的 `dependencies` 字段（dict）
- Node：存在 `package.json` 时执行 `npm install --omit=dev`
- Go：存在 `go.mod` 时执行 `go mod download`

Admin API：

- `POST /admin/plugins/{name}/deps/install?force=false`
- `GET /admin/plugins/{name}/deps/status`

---

## 9. 安装 / 卸载 / 运行时管理（Admin API）

所有 `/admin/*` 默认仅允许 localhost；如需远程访问，设置 `CERISE_ADMIN_TOKEN`。

常用端点：

- 安装：
  - `POST /admin/plugins/install/github?load=true`
  - `POST /admin/plugins/install/upload?load=true`（推荐直接发 zip bytes）
- 运行时：
  - `POST /admin/plugins/{name}/runtime/load|unload|reload`
  - `GET /admin/plugins/{name}/runtime`
  - `GET /admin/plugins/{name}/runtime/health`

示例（上传 zip bytes）：

```bash
curl -X POST \
  -H "Authorization: Bearer $CERISE_ADMIN_TOKEN" \
  -H "Content-Type: application/zip" \
  -H "X-Filename: my-plugin.zip" \
  --data-binary @my-plugin.zip \
  "http://127.0.0.1:8000/admin/plugins/install/upload?load=true"
```

---

## 10. 多语言 SDK（推荐）

仓库内提供了多语言最小 SDK：

- Python：`sdk/python/cerise_plugin/__init__.py`
- Node.js：`sdk/nodejs/cerise-plugin.js`
- Go：`sdk/go/cerise_plugin.go`
- C++：`sdk/cpp/cerise_plugin.hpp`

### 10.1 Python 示例

当前 Python SDK 位于仓库 `sdk/python/cerise_plugin/`。生产插件建议把该目录复制到你的插件目录（作为 `cerise_plugin` 包），然后按下述方式导入使用：

```python
from cerise_plugin import BasePlugin, AbilityContext, AbilityResult, run_plugin


class EchoPlugin(BasePlugin):
    def get_abilities(self) -> list[dict]:
        return [
            {
                "name": "echo",
                "description": "回显输入",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            }
        ]

    async def execute(self, ability: str, params: dict, context: AbilityContext) -> AbilityResult:
        if ability != "echo":
            return AbilityResult(success=False, error=f"Unknown ability: {ability}")
        return AbilityResult(success=True, data={"text": params.get("text", "")})


run_plugin(EchoPlugin())
```

### 10.2 Node.js 示例

当前 Node.js SDK 位于仓库 `sdk/nodejs/cerise-plugin.js`。生产插件建议把它复制到插件目录（或发布为 npm 包后再安装），例如：

```js
const { BasePlugin, runPlugin } = require('./cerise-plugin')
```

也可以参考仓库示例：`plugins/web-search/index.js`（它使用相对路径引用 SDK，仅适用于仓库内开发）。

### 10.3 Go 示例

参考：`sdk/go/cerise_plugin.go`。生产插件建议将 SDK vendoring 到你的插件仓库（或作为 module 引入），实现 `Plugin` 接口并调用 `ceriseplugin.Run(plugin)`。

### 10.4 C++ 示例

参考：`sdk/cpp/cerise_plugin.hpp`。建议用 `nlohmann/json`，实现 `cerise::Plugin` 并调用 `cerise::run(plugin)`（同样建议把 header vendoring 到插件项目中）。

---

## 11. 调试与最佳实践

- 能力命名：避免冲突；建议给 ability 加插件前缀。
- 输出大小：Core 会对 tool 结果做截断（默认 4000 chars），请返回“可读摘要”，大数据用分页/引用。
- 超时：默认 transport timeout 为 30s；长任务建议拆分或在插件内部做异步队列。
- Windows 命令行：若依赖 `runtime.command`，请自己处理好引号与路径空格。

相关实现（源码参考）：

- Core 插件协议与 transport：`apps/core/plugins/protocol_types.py`、`apps/core/plugins/transport_stdio.py`、`apps/core/plugins/transport_http.py`
- 插件生命周期：`apps/core/plugins/plugin_lifecycle.py`
- 插件安装与解包：`apps/core/plugins/installer_install.py`
- Admin API：`apps/core/api/admin/plugins.py`、`apps/core/api/admin/plugins_runtime.py`、`apps/core/api/admin/plugins_deps.py`、`apps/core/api/admin/stars.py`
