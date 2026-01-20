# Configuration Guide

## Main Configuration File

The main configuration file is located at `~/.cerise/config.yaml`.

```yaml
# Example configuration
server:
  host: "0.0.0.0"
  port: 8000

character:
  default: "default"

logging:
  level: "INFO"
```

## AI Provider Configuration

Provider configuration is located at `~/.cerise/providers.yaml`.

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

## Character Configuration

Character configuration files are located in the `~/.cerise/characters/` directory.

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
