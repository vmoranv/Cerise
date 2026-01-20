# 配置指南

## 主配置文件

主配置文件位于 `~/.cerise/config.yaml`。

```yaml
# 示例配置
server:
  host: "0.0.0.0"
  port: 8000

character:
  default: "default"

logging:
  level: "INFO"
```

## AI Provider 配置

Provider 配置位于 `~/.cerise/providers.yaml`。

```yaml
providers:
  openai:
    api_key: "your-api-key"
    model: "gpt-4"
  
  claude:
    api_key: "your-api-key"
    model: "claude-3-opus"
  
  gemini:
    api_key: "your-api-key"
    model: "gemini-pro"
```

## 记忆配置

记忆配置文件位于 `~/.cerise/memory.yaml`，示例配置见 `apps/core/config/examples/memory.yaml`。
详细使用方式与分层配置说明请参考 [记忆系统](./memory)。

## 角色配置

角色配置文件位于 `~/.cerise/characters/` 目录。

```yaml
# ~/.cerise/characters/default.yaml
name: "Cerise"
personality:
  traits:
    - friendly
    - helpful
  
emotion:
  default: neutral
```
