# TTS Server

基于 [Genie-TTS](https://github.com/High-Logic/Genie-TTS/) 的语音合成服务。

## 安装

```bash
uv sync
```

## 使用

### 启动服务

```bash
uv run python main.py
```

服务将在 `http://0.0.0.0:8000` 启动。

### 本地演示

```bash
uv run python demo.py
```

## 预置角色

- `mika` - 日语角色
- `feibi` - 中文角色

## API

参考 [Genie-TTS 文档](https://github.com/High-Logic/Genie-TTS/)。