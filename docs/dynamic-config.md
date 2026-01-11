# 动态配置系统

Cerise 使用 `~/.cerise/` 目录存储所有用户配置，实现代码与配置分离。

## 数据目录结构

```
~/.cerise/
├── config.yaml           # 主配置
├── providers.yaml        # AI Provider 配置
├── plugins.json          # 已安装插件列表
├── characters/           # 角色配置
│   └── default.yaml
├── plugins/              # 插件安装目录
├── logs/                 # 日志文件
└── cache/                # 缓存目录
```

## 配置文件

### config.yaml - 主配置

```yaml
server:
  host: 0.0.0.0
  port: 8000
  debug: false

ai:
  default_provider: openai
  default_model: gpt-4o
  temperature: 0.7
  max_tokens: 2048

plugins:
  enabled: true
  auto_start: true
  plugins_dir: ""  # 空 = 使用默认 ~/.cerise/plugins

tts:
  enabled: false
  provider: local
  character: default
  server_url: http://localhost:5000

logging:
  level: INFO
  file: ""  # 空 = 不写入文件
```

### providers.yaml - Provider 配置

```yaml
default: openai-1

providers:
  - id: openai-1
    type: openai
    name: OpenAI GPT-4
    enabled: true
    config:
      api_key: ${OPENAI_API_KEY}
      base_url: null
      model: gpt-4o

  - id: claude-1
    type: claude
    name: Claude 3.5 Sonnet
    enabled: false
    config:
      api_key: ${ANTHROPIC_API_KEY}

  - id: gemini-1
    type: gemini
    name: Google Gemini Pro
    enabled: false
    config:
      api_key: ${GOOGLE_API_KEY}
```

**环境变量支持**: 使用 `${VAR_NAME}` 语法引用环境变量。

### characters/default.yaml - 角色配置

```yaml
name: Cerise
language: zh

personality:
  openness: 0.7
  conscientiousness: 0.6
  extraversion: 0.7
  agreeableness: 0.8
  neuroticism: 0.3

voice:
  enabled: false
  character: default
  provider: local

system_prompt_template: ""
```

### plugins.json - 插件注册表

```json
{
  "plugins": [
    {
      "name": "web-search",
      "version": "1.0.0",
      "source": "github",
      "source_url": "https://github.com/user/cerise-web-search",
      "enabled": true,
      "installed_at": "2024-01-15T10:30:00"
    }
  ]
}
```

## WebUI 管理 API

所有 API 端点挂载在 `/admin` 路径下。

### 配置管理

| 端点            | 方法 | 功能         |
| --------------- | ---- | ------------ |
| `/admin/config` | GET  | 获取当前配置 |
| `/admin/config` | PUT  | 更新配置     |

### Provider 管理

| 端点                                | 方法   | 功能              |
| ----------------------------------- | ------ | ----------------- |
| `/admin/providers`                  | GET    | 列出所有 Provider |
| `/admin/providers`                  | POST   | 添加新 Provider   |
| `/admin/providers/{id}`             | PUT    | 更新 Provider     |
| `/admin/providers/{id}`             | DELETE | 删除 Provider     |
| `/admin/providers/{id}/test`        | POST   | 测试连接          |
| `/admin/providers/{id}/set-default` | POST   | 设为默认          |

### 角色管理

| 端点                       | 方法 | 功能         |
| -------------------------- | ---- | ------------ |
| `/admin/characters`        | GET  | 列出角色     |
| `/admin/characters/{name}` | GET  | 获取角色详情 |
| `/admin/characters/{name}` | PUT  | 更新角色     |

### 插件管理

| 端点                            | 方法   | 功能           |
| ------------------------------- | ------ | -------------- |
| `/admin/plugins`                | GET    | 列出已安装插件 |
| `/admin/plugins/install/github` | POST   | 从 GitHub 安装 |
| `/admin/plugins/install/upload` | POST   | 上传 zip 安装  |
| `/admin/plugins/{name}`         | GET    | 获取插件信息   |
| `/admin/plugins/{name}`         | PUT    | 更新插件配置   |
| `/admin/plugins/{name}`         | DELETE | 卸载插件       |
| `/admin/plugins/{name}/enable`  | POST   | 启用插件       |
| `/admin/plugins/{name}/disable` | POST   | 禁用插件       |

## API 示例

### 从 GitHub 安装插件

```bash
curl -X POST http://localhost:8000/admin/plugins/install/github \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/my-plugin", "branch": "main"}'
```

### 添加 Provider

```bash
curl -X POST http://localhost:8000/admin/providers \
  -H "Content-Type: application/json" \
  -d '{
    "id": "openai-2",
    "type": "openai",
    "name": "OpenAI Backup",
    "enabled": true,
    "config": {
      "api_key": "sk-xxx",
      "model": "gpt-4o-mini"
    }
  }'
```

### 测试 Provider 连接

```bash
curl -X POST http://localhost:8000/admin/providers/openai-1/test
```

响应：

```json
{
  "status": "ok",
  "latency_ms": 523.45,
  "model": "gpt-4o-2024-08-06"
}
```

### 上传 zip 安装插件

```bash
curl -X POST http://localhost:8000/admin/plugins/install/upload \
  -F "file=@my-plugin.zip"
```

## 编程接口

### ConfigLoader

```python
from apps.core.config import get_config_loader

loader = get_config_loader()

# 获取配置
app_config = loader.get_app_config()
providers_config = loader.get_providers_config()
character = loader.load_character_config("default")

# 修改配置
app_config.server.port = 9000
loader.save_app_config(app_config)

# 管理 Provider
from apps.core.config import ProviderConfig

new_provider = ProviderConfig(
    id="my-provider",
    type="openai",
    name="My Provider",
    config={"api_key": "sk-xxx"}
)
loader.add_provider(new_provider)
```

### ProviderRegistry

```python
from apps.core.ai.providers import ProviderRegistry

# 从配置加载 (首次访问时自动加载)
provider = ProviderRegistry.get("openai-1")

# 手动重新加载
ProviderRegistry.reload()

# 获取默认 Provider
default = ProviderRegistry.get_default()

# 列出所有实例
instances = ProviderRegistry.list_instances()

# 测试连接
result = await ProviderRegistry.test_connection("openai-1")
print(result)  # {"status": "ok", "latency_ms": 500.0, "model": "gpt-4o"}

# 获取 Provider 信息
info = ProviderRegistry.get_provider_info("openai-1")
```

### PluginInstaller

```python
from apps.core.plugins.installer import PluginInstaller

installer = PluginInstaller()

# 从 GitHub 安装
plugin = await installer.install_from_github(
    "https://github.com/user/my-plugin",
    branch="main"
)

# 从 zip 安装
plugin = await installer.install_from_zip("/path/to/plugin.zip")

# 列出已安装
plugins = installer.list_installed()

# 卸载
await installer.uninstall("my-plugin")
```

## 支持的 Provider 类型

| Type     | 说明             | 必需配置           |
| -------- | ---------------- | ------------------ |
| `openai` | OpenAI API       | `api_key`, `model` |
| `claude` | Anthropic Claude | `api_key`          |
| `gemini` | Google Gemini    | `api_key`          |

## 注意事项

1. **首次启动**: 如果配置文件不存在，系统会自动创建默认配置
2. **环境变量**: 推荐使用 `${VAR}` 语法引用敏感信息
3. **热重载**: 修改配置后调用 `ProviderRegistry.reload()` 可热重载
4. **私有仓库**: 当前只支持公共 GitHub 仓库，私有仓库请手动下载 zip 后上传