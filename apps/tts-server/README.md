# 语音服务 (Voice Server)

统一的语音服务，基于 [Genie-TTS](https://github.com/High-Logic/Genie-TTS/)（GPT-SoVITS 加速推理框架）构建，支持：

- **TTS（语音合成）**：高质量语音合成，支持多角色
- **ASR（语音识别）**：支持 FunASR、Whisper 本地推理
- **WebSocket**：实时语音流处理
- **双模式推理**：本地推理 + 云端 API

## 功能特性

### TTS 语音合成

- 基于 Genie-TTS（GPT-SoVITS 加速推理）
- ONNX Runtime 优化，推理速度快
- 支持中文、日语、英语
- 多角色语音支持
- HTTP API 和 WebSocket 流式输出

### ASR 语音识别

- **FunASR**：阿里巴巴语音识别框架
  - 支持流式识别
  - 中文识别效果优秀
  - 支持标点预测
- **Whisper**：OpenAI 语音识别模型
  - faster-whisper 优化版本
  - 多语言支持
  - 高准确率

### 云端 API 支持

- Azure Speech Services
- 阿里云语音服务
- 腾讯云语音服务
- 百度云语音服务

## 安装

### 基础安装

```bash
cd apps/tts-server
uv sync
```

### 本地 ASR 推理（可选）

安装 FunASR：

```bash
uv sync --extra funasr
```

安装 Whisper：

```bash
uv sync --extra whisper
```

安装所有本地推理依赖：

```bash
uv sync --extra local
```

### 开发依赖

```bash
uv sync --extra dev
```

## 快速开始

### 启动服务

```bash
# 使用默认配置启动
uv run voice-server

# 指定端口
uv run voice-server --port 8080

# 开发模式（热重载）
uv run voice-server --reload

# 查看帮助
uv run voice-server --help
```

### 环境变量配置

创建 `.env` 文件：

```env
# 推理模式：local（本地）或 cloud（云端）
INFERENCE_MODE=local

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# ASR 配置
ASR_PROVIDER=funasr  # funasr, whisper, azure, aliyun, tencent, baidu
ASR_MODEL=paraformer-zh

# TTS 配置
TTS_PROVIDER=genie_tts  # genie_tts, azure, aliyun, tencent, baidu
TTS_DEFAULT_CHARACTER=mika

# 云端 API 密钥（云端模式需要）
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=eastasia

ALIYUN_ACCESS_KEY_ID=your_key
ALIYUN_ACCESS_KEY_SECRET=your_secret
ALIYUN_APP_KEY=your_app_key

TENCENT_SECRET_ID=your_id
TENCENT_SECRET_KEY=your_key
TENCENT_APP_ID=your_app_id

BAIDU_API_KEY=your_key
BAIDU_SECRET_KEY=your_secret
```

### YAML 配置文件

也可以使用 YAML 配置文件 `config.yaml`：

```yaml
inference_mode: local

server:
  host: 0.0.0.0
  port: 8000
  workers: 1

asr:
  provider: funasr
  model: paraformer-zh
  language: zh
  enable_punctuation: true
  enable_streaming: true

tts:
  provider: genie_tts
  default_character: mika
  sample_rate: 44100
  format: wav

websocket:
  max_message_size: 10485760 # 10MB
  ping_interval: 30
  ping_timeout: 10
```

## API 文档

启动服务后访问：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### HTTP API

#### 健康检查

```bash
curl http://localhost:8000/health
```

#### TTS 语音合成

```bash
# 基础合成
curl -X POST http://localhost:8000/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，欢迎使用语音服务！", "character": "mika"}' \
  --output output.wav

# 流式输出
curl -X POST http://localhost:8000/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "这是一段较长的文本...", "stream": true}' \
  --output output.wav
```

#### ASR 语音识别

```bash
curl -X POST http://localhost:8000/asr/transcribe \
  -F "audio=@input.wav" \
  -F "language=zh"
```

### WebSocket API

#### 通用 WebSocket 端点

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// 发送控制消息
ws.send(
  JSON.stringify({
    type: 'config',
    mode: 'asr',
    language: 'zh',
  }),
);

// 发送音频数据
ws.send(audioData); // ArrayBuffer

// 接收结果
ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  console.log(result);
};
```

#### ASR 专用端点

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/asr');

// 开始识别
ws.send(JSON.stringify({ action: 'start', language: 'zh' }));

// 发送音频流
ws.send(audioChunk); // ArrayBuffer

// 结束识别
ws.send(JSON.stringify({ action: 'stop' }));
```

#### TTS 专用端点

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tts');

// 合成请求
ws.send(
  JSON.stringify({
    text: '你好世界',
    character: 'mika',
  }),
);

// 接收音频流
ws.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    // 音频数据
    playAudio(event.data);
  } else {
    // 状态消息
    const status = JSON.parse(event.data);
    console.log(status);
  }
};
```

## 项目结构

```
apps/tts-server/
├── src/
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── server.py          # 主服务器
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py      # API 路由
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── base.py        # ASR 抽象基类
│   │   ├── factory.py     # ASR 工厂
│   │   ├── funasr_engine.py   # FunASR 引擎
│   │   ├── whisper_engine.py  # Whisper 引擎
│   │   └── cloud_client.py    # 云端 ASR 客户端
│   ├── tts/
│   │   ├── __init__.py
│   │   └── adapter.py     # TTS 适配器
│   └── websocket/
│       ├── __init__.py
│       ├── manager.py     # 连接管理器
│       └── handler.py     # 消息处理器
├── demo.py                # 演示脚本
├── main.py                # 简单入口（兼容旧版）
├── pyproject.toml         # 项目配置
├── config.yaml            # 配置文件示例
└── README.md
```

## 预置角色

服务预置了以下角色模型：

| 角色  | 语言 | 说明         |
| ----- | ---- | ------------ |
| mika  | 日语 | 日语女声角色 |
| feibi | 中文 | 中文女声角色 |

### 自定义角色

将角色模型放置在 `CharacterModels/v2ProPlus/` 目录下：

```
CharacterModels/v2ProPlus/
├── your_character/
│   ├── prompt_wav/        # 参考音频
│   └── tts_models/        # 模型文件
```

## 性能优化

### GPU 加速

确保安装了 CUDA 版本的 PyTorch：

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 模型预加载

通过环境变量配置默认角色，服务启动时会自动预加载：

```env
TTS_DEFAULT_CHARACTER=mika
```

### 多进程

生产环境可以启用多工作进程：

```bash
uv run voice-server --workers 4
```

## 开发

### 运行测试

```bash
uv run pytest
```

### 代码检查

```bash
uv run ruff check src/
uv run mypy src/
```

### 格式化

```bash
uv run ruff format src/
```

## 许可证

本项目遵循 Genie-TTS 的许可证条款。

## 致谢

- [Genie-TTS](https://github.com/High-Logic/Genie-TTS/) - GPT-SoVITS 加速推理框架
- [FunASR](https://github.com/alibaba-damo-academy/FunASR) - 阿里巴巴语音识别框架
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Whisper 优化实现
