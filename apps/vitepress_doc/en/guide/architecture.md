# Architecture Overview

This document describes the overall architecture design of the Cerise project.

## Project Structure

```
Cerise/
├── apps/                          # Applications
│   ├── core/                      # Python Core Service
│   │   ├── abilities/             # Ability System
│   │   │   ├── builtin/           # Built-in abilities (computer_use, python_runner)
│   │   │   └── plugins/           # Plugin abilities
│   │   ├── ai/                    # AI Module
│   │   │   ├── dialogue/          # Dialogue Engine
│   │   │   ├── emotion/           # Emotion Engine
│   │   │   ├── memory/            # Memory System
│   │   │   └── providers/         # AI Provider implementations
│   │   ├── api/                   # REST API (FastAPI)
│   │   ├── character/             # Character System
│   │   │   ├── emotion/           # Emotion State Machine
│   │   │   └── personality/       # Personality Model
│   │   ├── config/                # Configuration Loader
│   │   ├── contracts/             # Protocol/Interface Definitions
│   │   ├── infrastructure/        # Infrastructure (events, state)
│   │   ├── l2d/                   # Live2D Service
│   │   ├── plugins/               # Plugin Manager
│   │   └── services/              # Service Layer
│   ├── tts-server/                # TTS Service (Python)
│   ├── cerise_webui/              # Web Frontend
│   └── vitepress_doc/             # Documentation Site
├── plugins/                       # Plugin Examples
│   ├── pixiv-search/              # Pixiv Search Plugin
│   ├── vts-driver/                # VTube Studio Driver
│   └── web-search/                # Web Search Plugin
├── sdk/                           # Plugin Development SDK
│   ├── nodejs/                    # Node.js SDK
│   └── python/                    # Python SDK
└── docs/                          # Original Documentation
```

## Architecture Diagram

```text
graph TB
    subgraph "Client Layer"
        WebUI[Web UI]
        L2D[Live2D Viewer]
        API_Client[API Client]
    end

    subgraph "API Gateway"
        Gateway[FastAPI Gateway]
    end

    subgraph "Core Services"
        DialogueEngine[Dialogue Engine]
        EmotionEngine[Emotion Engine]
        MemoryEngine[Memory Engine]
        CharacterSystem[Character System]
    end

    subgraph "AI Provider"
        OpenAI[OpenAI]
        Claude[Claude]
        Gemini[Gemini]
        CustomProvider[Custom Provider]
    end

    subgraph "Plugin System"
        PluginManager[Plugin Manager]
        PluginBridge[Plugin Bridge]
        Abilities[Ability Registry]
    end

    subgraph "External Services"
        TTS[TTS Service]
        L2DService[Live2D Service]
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

## Core Modules

### 1. Dialogue Engine

The dialogue engine handles user input and coordinates AI Provider, emotion engine, and memory system.

**Key Files:**
- `apps/core/ai/dialogue/engine.py` - Dialogue engine core
- `apps/core/ai/dialogue/session.py` - Session management

### 2. AI Provider System

Unified abstraction layer supporting multiple AI service providers.

**Key Files:**
- `apps/core/ai/providers/base.py` - Provider base class
- `apps/core/ai/providers/openai_provider.py` - OpenAI implementation
- `apps/core/ai/providers/claude_provider.py` - Claude implementation
- `apps/core/ai/providers/gemini_provider.py` - Gemini implementation
- `apps/core/ai/providers/registry.py` - Provider registry

### 3. Emotion Engine

Rule and lexicon-based emotion analysis system for recognizing and generating emotional states.

**Key Files:**
- `apps/core/ai/emotion/analyzer.py` - Emotion analyzer
- `apps/core/ai/emotion/lexicon.py` - Emotion lexicon
- `apps/core/ai/emotion/rules.py` - Emotion rules
- `apps/core/ai/emotion/pipeline.py` - Emotion processing pipeline
- `apps/core/character/emotion/state_machine.py` - Emotion state machine

### 4. Memory System

Intelligent memory management supporting short-term memory, long-term memory, and knowledge graphs.

**Key Files:**
- `apps/core/ai/memory/engine.py` - Memory engine
- `apps/core/ai/memory/store.py` - Memory store
- `apps/core/ai/memory/sqlite_store.py` - SQLite storage implementation
- `apps/core/ai/memory/vector_index.py` - Vector index
- `apps/core/ai/memory/kg.py` - Knowledge graph
- `apps/core/ai/memory/retrieval.py` - Memory retrieval

### 5. Character System

Manages virtual character personality and emotional state.

**Key Files:**
- `apps/core/character/personality/model.py` - Personality model
- `apps/core/character/emotion/state_machine.py` - Emotion state machine

### 6. Plugin System

Flexible plugin architecture supporting Python and Node.js plugins.

**Key Files:**
- `apps/core/plugins/manager.py` - Plugin manager
- `apps/core/plugins/bridge.py` - Plugin bridge layer
- `apps/core/plugins/protocol.py` - Plugin communication protocol
- `apps/core/plugins/transport.py` - Transport layer
- `apps/core/abilities/registry.py` - Ability registry
- `apps/core/abilities/loader.py` - Ability loader

### 7. API Gateway

FastAPI-based REST API gateway.

**Key Files:**
- `apps/core/api/gateway.py` - API gateway
- `apps/core/api/admin.py` - Admin endpoints
- `apps/core/api/container.py` - Dependency injection container

## Data Flow

```text
sequenceDiagram
    participant User as User
    participant API as API Gateway
    participant Dialogue as Dialogue Engine
    participant Memory as Memory System
    participant AI as AI Provider
    participant Emotion as Emotion Engine
    participant Character as Character System

    User->>API: Send message
    API->>Dialogue: Process request
    Dialogue->>Memory: Retrieve relevant memories
    Memory-->>Dialogue: Return memory context
    Dialogue->>AI: Generate response
    AI-->>Dialogue: AI response
    Dialogue->>Emotion: Analyze emotion
    Emotion-->>Dialogue: Emotion state
    Dialogue->>Character: Update character state
    Dialogue->>Memory: Store new memory
    Dialogue-->>API: Return response
    API-->>User: Display reply
```

## Tech Stack

### Backend (Python)
- **Python 3.11+**
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **PyYAML** - Configuration parsing
- **httpx** - HTTP client
- **SQLite** - Local storage

### Frontend (Node.js)
- **pnpm** - Package manager
- **TypeScript** - Type safety
- **Rolldown** - Bundler
- **VitePress** - Documentation site

## Configuration

User data is stored in the `~/.cerise/` directory:

```
~/.cerise/
├── config.yaml          # Main configuration file
├── providers.yaml       # AI Provider configuration
├── characters/          # Character configurations
│   └── *.yaml
├── plugins/             # Installed plugins
└── plugins.json         # Plugin registry
```
