# 架构概览

本文档介绍 Cerise 项目的整体架构设计。

## 项目结构

```
Cerise/
├── apps/                          # 应用程序
│   ├── core/                      # Python 核心服务
│   │   ├── abilities/             # 能力系统
│   │   │   ├── builtin/           # 内置能力 (computer_use, python_runner)
│   │   │   └── plugins/           # 插件能力
│   │   ├── ai/                    # AI 模块
│   │   │   ├── dialogue/          # 对话引擎
│   │   │   ├── emotion/           # 情感引擎
│   │   │   ├── memory/            # 记忆系统
│   │   │   └── providers/         # AI Provider 实现
│   │   ├── api/                   # REST API (FastAPI)
│   │   ├── character/             # 角色系统
│   │   │   ├── emotion/           # 情感状态机
│   │   │   └── personality/       # 人格模型
│   │   ├── config/                # 配置加载器
│   │   ├── contracts/             # 协议/接口定义
│   │   ├── infrastructure/        # 基础设施 (事件、状态)
│   │   ├── l2d/                   # Live2D 服务
│   │   ├── plugins/               # 插件管理器
│   │   └── services/              # 服务层
│   ├── tts-server/                # TTS 服务 (Python)
│   ├── cerise_webui/              # Web 前端
│   └── vitepress_doc/             # 文档站点
├── plugins/                       # 插件示例
│   ├── pixiv-search/              # Pixiv 搜索插件
│   ├── vts-driver/                # VTube Studio 驱动
│   └── web-search/                # 网页搜索插件
├── sdk/                           # 插件开发 SDK
│   ├── nodejs/                    # Node.js SDK
│   └── python/                    # Python SDK
└── docs/                          # 原始文档
```

## 架构图

```text
graph TB
    subgraph "客户端层"
        WebUI[Web UI]
        L2D[Live2D Viewer]
        API_Client[API 客户端]
    end

    subgraph "API 网关"
        Gateway[FastAPI Gateway]
    end

    subgraph "核心服务"
        DialogueEngine[对话引擎]
        EmotionEngine[情感引擎]
        MemoryEngine[记忆引擎]
        CharacterSystem[角色系统]
    end

    subgraph "AI Provider"
        OpenAI[OpenAI]
        Claude[Claude]
        Gemini[Gemini]
        CustomProvider[自定义 Provider]
    end

    subgraph "插件系统"
        PluginManager[插件管理器]
        PluginBridge[插件桥接]
        Abilities[能力注册]
    end

    subgraph "外部服务"
        TTS[TTS 服务]
        L2DService[Live2D 服务]
    end

    WebUI --> Gateway
    L2D --> Gateway
    API_Client --> Gateway

    Gateway --> DialogueEngine
    Gateway --> CharacterSystem
    Gateway --> PluginManager

    DialogueEngine --> EmotionEngine
    DialogueEngine --> MemoryEngine
    DialogueEngine --> OpenAI
    DialogueEngine --> Claude
    DialogueEngine --> Gemini
    DialogueEngine --> CustomProvider

    CharacterSystem --> EmotionEngine

    PluginManager --> PluginBridge
    PluginBridge --> Abilities

    Gateway --> TTS
    Gateway --> L2DService
```

## 核心模块

### 1. 对话引擎 (Dialogue Engine)

对话引擎负责处理用户输入，协调 AI Provider、情感引擎和记忆系统。

**关键文件:**
- `apps/core/ai/dialogue/engine.py` - 对话引擎核心
- `apps/core/ai/dialogue/session.py` - 会话管理

### 2. AI Provider 系统

支持多种 AI 服务商的统一抽象层。

**关键文件:**
- `apps/core/ai/providers/base.py` - Provider 基类
- `apps/core/ai/providers/openai_provider.py` - OpenAI 实现
- `apps/core/ai/providers/claude_provider.py` - Claude 实现
- `apps/core/ai/providers/gemini_provider.py` - Gemini 实现
- `apps/core/ai/providers/registry.py` - Provider 注册表

### 3. 情感引擎 (Emotion Engine)

基于规则和词典的情感分析系统，用于识别和生成情感状态。

**关键文件:**
- `apps/core/ai/emotion/analyzer.py` - 情感分析器
- `apps/core/ai/emotion/lexicon.py` - 情感词典
- `apps/core/ai/emotion/rules.py` - 情感规则
- `apps/core/ai/emotion/pipeline.py` - 情感处理管道
- `apps/core/character/emotion/state_machine.py` - 情感状态机

### 4. 记忆系统 (Memory System)

智能记忆管理，支持短期记忆、长期记忆和知识图谱。

**关键文件:**
- `apps/core/ai/memory/engine.py` - 记忆引擎
- `apps/core/ai/memory/store.py` - 记忆存储
- `apps/core/ai/memory/sqlite_store.py` - SQLite 存储实现
- `apps/core/ai/memory/vector_index.py` - 向量索引
- `apps/core/ai/memory/kg.py` - 知识图谱
- `apps/core/ai/memory/retrieval.py` - 记忆检索

### 5. 角色系统 (Character System)

管理虚拟角色的人格和情感状态。

**关键文件:**
- `apps/core/character/personality/model.py` - 人格模型
- `apps/core/character/emotion/state_machine.py` - 情感状态机

### 6. 插件系统 (Plugin System)

灵活的插件架构，支持 Python 和 Node.js 插件。

**关键文件:**
- `apps/core/plugins/manager.py` - 插件管理器
- `apps/core/plugins/bridge.py` - 插件桥接层
- `apps/core/plugins/protocol.py` - 插件通信协议
- `apps/core/plugins/transport.py` - 传输层
- `apps/core/abilities/registry.py` - 能力注册表
- `apps/core/abilities/loader.py` - 能力加载器

### 7. API 网关

基于 FastAPI 的 REST API 网关。

**关键文件:**
- `apps/core/api/gateway.py` - API 网关
- `apps/core/api/admin.py` - 管理端点
- `apps/core/api/container.py` - 依赖注入容器

## 数据流

```text
sequenceDiagram
    participant User as 用户
    participant API as API 网关
    participant Dialogue as 对话引擎
    participant Memory as 记忆系统
    participant AI as AI Provider
    participant Emotion as 情感引擎
    participant Character as 角色系统

    User->>API: 发送消息
    API->>Dialogue: 处理请求
    Dialogue->>Memory: 检索相关记忆
    Memory-->>Dialogue: 返回记忆上下文
    Dialogue->>AI: 生成回复
    AI-->>Dialogue: AI 响应
    Dialogue->>Emotion: 分析情感
    Emotion-->>Dialogue: 情感状态
    Dialogue->>Character: 更新角色状态
    Dialogue->>Memory: 存储新记忆
    Dialogue-->>API: 返回响应
    API-->>User: 显示回复
```

## 技术栈

### 后端 (Python)
- **Python 3.11+**
- **FastAPI** - Web 框架
- **Pydantic** - 数据验证
- **PyYAML** - 配置解析
- **httpx** - HTTP 客户端
- **SQLite** - 本地存储

### 前端 (Node.js)
- **pnpm** - 包管理器
- **TypeScript** - 类型安全
- **Rolldown** - 打包工具
- **VitePress** - 文档站点

## 配置

用户数据存储在 `~/.cerise/` 目录:

```
~/.cerise/
├── config.yaml          # 主配置文件
├── providers.yaml       # AI Provider 配置
├── characters/          # 角色配置
│   └── *.yaml
├── plugins/             # 已安装插件
└── plugins.json         # 插件注册表
```
