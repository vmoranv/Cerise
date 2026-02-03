# Cerise 🌸

<div align="center">

**一个基于 Live2D 的智能 AI 对话助手**

[![Next.js](https://img.shields.io/badge/Next.js-16.1.2-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.2.3-61dafb?style=flat-square&logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178c6?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-AGPLv3-blue?style=flat-square)](LICENSE)

<img src="https://img.shields.io/badge/🌸_Cerise-樱桃粉主题-de3163?style=for-the-badge" alt="Cerise Theme" />

*优雅 · 智能 · 情感化*

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [项目结构](#-项目结构) • [文档](#-文档) • [贡献](#-贡献)

</div>

---

## 📖 简介

**Cerise** 是一个现代化的 AI 智能助手系统，以"Cerise"（法语：樱桃粉）为设计灵感，提供：

- 🎨 **艺术化设计** - 樱花粉主题色系，优雅的渐变效果
- 🤖 **智能对话** - 支持多种 AI Provider（OpenAI、Claude、Gemini 等）
- 💬 **情感系统** - 12 种情感状态的实时可视化
- 🎭 **Live2D 集成** - 虚拟角色动画展示
- 🎙️ **语音交互** - TTS 语音合成 & ASR 语音识别
- 🔌 **插件系统** - 可扩展的能力架构
- 🌓 **暗色模式** - 自适应主题切换

---

## ✨ 功能特性

### 🎨 前端界面

- **现代化设计**
  - Cerise 樱花粉主题色系 (#de3163)
  - 玻璃态效果（毛玻璃背景）
  - 流畅的 Framer Motion 动画
  - 响应式布局，支持移动端

- **聊天系统**
  - 实时消息发送和接收
  - 消息气泡设计（用户/AI 区分）
  - 支持 Markdown 渲染
  - 自动滚动到最新消息

- **情感可视化**
  - 12 种情感状态（开心、伤心、思考、害羞等）
  - 每种情感独特的颜色和图标
  - 情感强度进度条
  - 动态脉冲效果

- **Live2D 支持**
  - Live2D 模型显示容器
  - 情感参数实时同步
  - 可显示/隐藏控制

### 🤖 后端服务

- **Core API** (FastAPI)
  - 多 Provider 支持（15+ AI 服务）
  - 对话引擎（支持工具调用、流式响应）
  - 记忆引擎（向量检索）
  - 情感分析系统
  - 插件管理（stdio/http 传输）
  - 配置管理 API

- **TTS Server** (FastAPI)
  - TTS 语音合成（Genie-TTS / 云端 API）
  - ASR 语音识别（FunASR / Whisper）
  - WebSocket 流式支持
  - 多角色语音切换

### 🔧 技术亮点

- **前端**
  - Next.js 16 (App Router)
  - React 19 (Server Components)
  - Tailwind CSS 4
  - Zustand 状态管理
  - TypeScript 完整类型支持

- **后端**
  - FastAPI (异步高性能)
  - Pydantic 数据验证
  - 依赖注入架构
  - 事件驱动设计（消息总线）
  - 插件系统（JSON-RPC 协议）

---

## 🚀 快速开始

### 前置要求

- **Node.js** 20+ 和 **pnpm** 8+
- **Python** 3.10+
- **uv** (Python 包管理器) - `pip install uv`
- **Git**

### 方法 1: 一键启动（推荐）

#### Windows
```bash
git clone https://github.com/your-repo/cerise.git
cd cerise
.\start.bat
```

选择 **1) 全部启动**，等待服务启动完成。

#### Linux / macOS
```bash
git clone https://github.com/your-repo/cerise.git
cd cerise
chmod +x start.sh
./start.sh
```

选择 **1. Start All**，等待服务启动完成。

### 停止所有服务

如果需要停止所有运行中的 Cerise 服务：

#### Windows
```bash
.\stop.bat
```

#### Linux / macOS
```bash
chmod +x stop.sh
./stop.sh
```

此脚本会：
- 停止所有端口（8000, 8001, 3000, 3001）上的进程
- 清理 Next.js 锁文件
- 释放所有资源

### 方法 2: 分步启动

#### 1. 安装依赖

```bash
# 前端依赖
cd apps/cerise_webui
pnpm install
cd ../..

# 后端依赖（使用 uv）
cd apps/core
uv sync
cd ../..
```

#### 2. 配置环境

**前端配置** (`apps/cerise_webui/.env.local`):
```env
NEXT_PUBLIC_CORE_API_URL=http://localhost:8000
NEXT_PUBLIC_TTS_API_URL=http://localhost:8001
```

**后端配置** (`apps/core/config.yaml`):
```yaml
server:
  host: 0.0.0.0
  port: 8000

ai:
  default_provider: openai
  default_model: gpt-4o
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}  # 设置环境变量
```

#### 3. 启动服务

```bash
# 终端 1: Core API
cd apps/core
uv run python main.py

# 终端 2: TTS Server (可选)
cd apps/tts-server
uv run python main.py

# 终端 3: Web UI
cd apps/cerise_webui
pnpm dev
```

#### 4. 访问应用

打开浏览器访问: **http://localhost:3000**

---

## 📂 项目结构

```
Cerise/
├── apps/
│   ├── cerise_webui/              # 🌸 前端 (Next.js)
│   │   ├── app/                  # Next.js App Router
│   │   │   ├── page.tsx         # 主页（聊天界面）
│   │   │   ├── layout.tsx       # 根布局
│   │   │   └── globals.css      # 全局样式（Cerise 主题）
│   │   ├── components/           # React 组件
│   │   │   ├── ChatInterface.tsx # 主聊天界面
│   │   │   ├── ui/              # 基础 UI 组件
│   │   │   ├── chat/            # 聊天组件
│   │   │   └── live2d/          # Live2D 组件
│   │   ├── lib/                 # API 服务层
│   │   ├── stores/              # Zustand 状态管理
│   │   ├── types/               # TypeScript 类型
│   │   └── package.json
│   │
│   ├── core/                      # 🧠 Core API (FastAPI)
│   │   ├── main.py              # 应用入口
│   │   ├── config.yaml          # 配置文件
│   │   ├── api/                 # API 路由
│   │   │   ├── gateway.py      # 主路由
│   │   │   └── admin.py        # 管理路由
│   │   ├── ai/                  # AI 引擎
│   │   │   ├── dialogue/       # 对话引擎
│   │   │   ├── emotion/        # 情感分析
│   │   │   ├── memory/         # 记忆引擎
│   │   │   └── providers/      # AI Provider
│   │   ├── abilities/           # 能力系统
│   │   ├── plugins/             # 插件管理
│   │   ├── character/           # 角色配置
│   │   ├── l2d/                # Live2D 服务
│   │   └── requirements.txt
│   │
│   └── tts-server/                # 🎙️ TTS Server (FastAPI)
│       ├── server.py            # 服务入口
│       ├── config.yaml          # TTS 配置
│       ├── src/
│       │   ├── api/            # TTS/ASR API
│       │   ├── tts/            # TTS 引擎
│       │   ├── asr/            # ASR 引擎
│       │   └── websocket/      # WebSocket 处理
│       └── requirements.txt
│
├── docs/                          # 📚 文档
├── start.sh                       # Linux/Mac 启动脚本
├── start.bat                      # Windows 启动脚本
├── package.json                   # 根配置
├── pnpm-workspace.yaml           # pnpm 工作区
├── FRONTEND_COMPLETE.md          # 前端完整文档
└── README.md                      # 本文件
```

---

## 🔌 API 端点

### Core API (`http://localhost:8000`)

#### 聊天相关
- `POST /sessions` - 创建会话
- `GET /sessions/{id}` - 获取会话信息
- `DELETE /sessions/{id}` - 删除会话
- `POST /chat` - 发送消息（非流式）
- `WebSocket /ws/chat` - 流式聊天

#### 情感相关
- `GET /emotion` - 获取当前情感
- `POST /emotion` - 手动设置情感
- `POST /l2d/emotion` - 设置 Live2D 情感参数

#### 管理端点 (`/admin/*`)
- `GET /admin/config` - 获取应用配置
- `GET /admin/providers` - 列出 AI Providers
- `POST /admin/providers/{id}/test` - 测试 Provider
- `GET /admin/plugins` - 列出插件
- `GET /admin/characters` - 列出角色

### TTS Server (`http://localhost:8001`)

- `POST /api/v1/tts/synthesize/audio` - 文本转语音
- `POST /api/v1/asr/transcribe` - 语音识别
- `GET /api/v1/tts/characters` - 获取可用角色
- `WebSocket /ws/tts` - TTS 流式
- `WebSocket /ws/asr` - ASR 流式

完整 API 文档见 [API Documentation](docs/API.md)

---

## 🎨 主题定制

Cerise 使用樱花粉主题色系，可在 [apps/cerise_webui/app/globals.css](apps/cerise_webui/app/globals.css) 中自定义：

```css
:root {
  /* Cerise 主题色 */
  --cerise-primary: #de3163;  /* 樱桃粉 */
  --cerise-light: #ff6b9d;    /* 樱花粉 */
  --cerise-dark: #c72c5c;     /* 玫瑰红 */

  /* 渐变色 */
  --gradient-cerise: linear-gradient(135deg, #ff6b9d 0%, #de3163 50%, #c72c5c 100%);
}
```

---

## 🧩 支持的 AI Providers

Cerise 支持 15+ AI 服务商：

| Provider | 类型 | 支持模型 |
|----------|------|----------|
| OpenAI | 云端 | GPT-4, GPT-3.5 |
| Claude / Anthropic | 云端 | Claude 3 系列 |
| Google Gemini | 云端 | Gemini Pro/Flash |
| Groq | 云端 | Llama, Mixtral |
| DeepSeek | 云端 | DeepSeek Chat |
| Moonshot | 云端 | Moonshot v1 |
| Zhipu AI | 云端 | GLM-4 |
| Qwen | 云端 | 通义千问 |
| Ollama | 本地 | 所有 Ollama 模型 |
| LM Studio | 本地 | 所有本地模型 |

配置方法见 [Provider 配置文档](docs/PROVIDERS.md)

---

## 📚 文档

- **[FRONTEND_COMPLETE.md](FRONTEND_COMPLETE.md)** - 前端完整说明
- **[FRONTEND_SUMMARY.md](FRONTEND_SUMMARY.md)** - 前端详细总结
- **[apps/cerise_webui/README_WEBUI.md](apps/cerise_webui/README_WEBUI.md)** - Web UI 使用指南
- **[apps/cerise_webui/STARTUP_GUIDE.md](apps/cerise_webui/STARTUP_GUIDE.md)** - 启动指南

---

## 🛠️ 开发指南

### 添加新的 AI Provider

1. 在 `apps/core/ai/providers/` 创建 Provider 类
2. 继承 `BaseProvider` 并实现必要方法
3. 在 `registry.py` 中注册 Provider

### 开发新插件

```python
# plugins/my_plugin/main.py
from cerise.plugins import Plugin, tool

class MyPlugin(Plugin):
    @tool(description="我的工具")
    async def my_tool(self, param: str) -> str:
        return f"处理: {param}"
```

### 前端添加新组件

```tsx
// components/MyComponent.tsx
'use client';

import { motion } from 'framer-motion';

export function MyComponent() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-lg bg-cerise-primary"
    >
      {/* 内容 */}
    </motion.div>
  );
}
```

---

## 🐛 故障排除

### API 连接失败
- 检查后端服务是否启动
- 检查 `.env.local` 配置
- 查看浏览器控制台的网络请求

### 端口被占用

如果遇到端口冲突错误（例如：`address already in use`、`EADDRINUSE`）：

```bash
# 方法 1: 使用停止脚本（推荐）
.\stop.bat          # Windows
./stop.sh           # Linux/Mac

# 方法 2: 手动停止
# Windows - 查找并杀死进程
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac - 查找并杀死进程
lsof -ti:8000 | xargs kill -9
```

### 构建错误

```bash
# 清除缓存重新构建
cd apps/cerise_webui
rm -rf .next node_modules
pnpm install
pnpm build
```

### Python 依赖问题

```bash
# 使用 uv 重新同步依赖
cd apps/core
uv sync

# 或清除缓存后重新安装
rm -rf .venv
uv sync
```

### Next.js 锁文件冲突

如果看到 "Unable to acquire lock" 错误：

```bash
# 删除锁文件
rm -f apps/cerise_webui/.next/dev/lock

# 或使用停止脚本自动清理
.\stop.bat          # Windows
./stop.sh           # Linux/Mac
```

---

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献指南

- 遵循现有代码风格
- 添加必要的测试
- 更新相关文档
- 提交前运行 linter

---

## 📄 开源协议

本项目采用 [GNU AGPLv3](LICENSE) 开源协议。

---

## 🙏 致谢

感谢以下开源项目：

- [Next.js](https://nextjs.org/) - React 框架
- [FastAPI](https://fastapi.tiangolo.com/) - Python Web 框架
- [Tailwind CSS](https://tailwindcss.com/) - CSS 框架
- [Framer Motion](https://www.framer.com/motion/) - 动画库
- [Zustand](https://github.com/pmndrs/zustand) - 状态管理
- [Live2D](https://www.live2d.com/) - 虚拟角色技术

---

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/your-repo/cerise/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/cerise/discussions)

---

## 🌟 Star History

如果觉得这个项目有帮助，请给个 ⭐️ Star！

---

<div align="center">

**Made with ❤️ and 🌸**

*Cerise - 让 AI 对话更优雅*

[返回顶部](#cerise-)

</div>
