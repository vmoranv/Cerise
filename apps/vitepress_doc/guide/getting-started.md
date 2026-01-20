# 快速开始

## 环境要求

- Python 3.11+
- Node.js 18+
- pnpm

## 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/cerise.git
cd cerise

# 安装依赖
pnpm install

# 安装 Python 依赖
cd apps/core
uv sync
```

## 启动服务

```bash
# 启动核心服务
cd apps/core
uv run python main.py

# 启动 TTS 服务 (可选)
cd apps/tts-server
uv run python main.py
```

## 配置

首次运行会在 `~/.cerise/` 创建默认配置文件，你可以编辑这些文件来自定义设置。

详细配置说明请参考 [配置指南](./configuration.md)。
