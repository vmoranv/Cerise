"""
统一语音服务器

整合 ASR、TTS 和 WebSocket 功能的主服务器
"""

import argparse
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import setup_routes
from .asr.factory import ASREngineFactory
from .config import get_config
from .tts.adapter import TTSAdapterFactory

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============ 应用生命周期管理 ============


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时初始化 ASR 和 TTS 引擎
    关闭时清理资源
    """
    config = get_config()
    logger.info("正在启动语音服务器...")
    logger.info(f"推理模式: {config.inference_mode.value}")
    logger.info(f"ASR 提供者: {config.asr.provider.value}")
    logger.info(f"TTS 提供者: {config.tts.provider.value}")

    # 初始化 ASR 引擎
    try:
        asr_engine = await ASREngineFactory.create(config)
        if asr_engine:
            logger.info("ASR 引擎初始化成功")
        else:
            logger.warning("ASR 引擎未配置或初始化失败")
    except Exception as e:
        logger.error(f"ASR 引擎初始化失败: {e}")

    # 初始化 TTS 适配器
    try:
        tts_adapter = await TTSAdapterFactory.create(config)
        if tts_adapter:
            logger.info("TTS 适配器初始化成功")
        else:
            logger.warning("TTS 适配器未配置或初始化失败")
    except Exception as e:
        logger.error(f"TTS 适配器初始化失败: {e}")

    # 预加载角色模型（本地模式）
    if config.tts.provider.value == "genie_tts":
        try:
            import genie_tts as genie

            default_char = config.tts.default_character
            logger.info(f"预加载默认角色: {default_char}")
            genie.load_predefined_character(default_char)
            logger.info(f"角色 {default_char} 加载成功")
        except Exception as e:
            logger.warning(f"预加载角色失败: {e}")

    logger.info("语音服务器启动完成")

    yield

    # 清理资源
    logger.info("正在关闭语音服务器...")

    # 清理 ASR 引擎
    try:
        await ASREngineFactory.cleanup()
        logger.info("ASR 引擎已清理")
    except Exception as e:
        logger.error(f"清理 ASR 引擎失败: {e}")

    # 清理 TTS 适配器
    try:
        await TTSAdapterFactory.cleanup()
        logger.info("TTS 适配器已清理")
    except Exception as e:
        logger.error(f"清理 TTS 适配器失败: {e}")

    logger.info("语音服务器已关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    """
    app = FastAPI(
        title="语音服务 API",
        description="""
        统一的语音服务 API，支持：

        - **ASR（语音识别）**：支持 FunASR、Whisper 本地推理和云端 API
        - **TTS（语音合成）**：基于 Genie-TTS（GPT-SoVITS 加速推理）
        - **WebSocket**：实时语音流处理

        ## 推理模式

        - `local`：本地推理模式，使用本地 GPU/CPU 进行推理
        - `cloud`：云端推理模式，通过 API 调用云端服务

        ## WebSocket 端点

        - `/ws`：通用 WebSocket 端点
        - `/ws/asr`：ASR 专用端点
        - `/ws/tts`：TTS 专用端点
        """,
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 设置 API 路由
    setup_routes(app)

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8001,
    workers: int = 1,
    reload: bool = False,
    log_level: str = "info",
):
    """
    运行服务器

    Args:
        host: 绑定地址
        port: 端口号
        workers: 工作进程数
        reload: 是否启用热重载
        log_level: 日志级别
    """
    config = get_config()

    # 使用配置文件中的设置（如果未指定）
    host = host or config.server.host
    port = port or config.server.port
    workers = workers or config.server.workers

    logger.info(f"启动服务器: {host}:{port}")
    logger.info(f"工作进程数: {workers}")
    logger.info(f"推理模式: {config.inference_mode.value}")

    uvicorn.run(
        "src.server:create_app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level=log_level,
        factory=True,
    )


def run_with_genie(host: str = "0.0.0.0", port: int = 8001, workers: int = 1):
    """
    使用 Genie-TTS 内置服务器运行

    这种模式下，使用 Genie-TTS 的内置 FastAPI 服务器，
    并在其基础上添加 ASR 和 WebSocket 功能
    """
    # 创建我们的应用
    app = create_app()

    # 启动服务
    logger.info(f"使用 Genie-TTS 模式启动服务器: {host}:{port}")

    uvicorn.run(app, host=host, port=port, workers=workers, log_level="info")


# ============ CLI 入口 ============


def main():
    """
    命令行入口
    """
    parser = argparse.ArgumentParser(description="语音服务器 - 支持 ASR + TTS + WebSocket")

    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定地址（默认: 0.0.0.0）")

    parser.add_argument("--port", type=int, default=8001, help="端口号（默认: 8001）")

    parser.add_argument("--workers", type=int, default=1, help="工作进程数（默认: 1）")

    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别（默认: info）",
    )

    parser.add_argument(
        "--mode",
        type=str,
        default="standalone",
        choices=["standalone", "genie"],
        help="运行模式: standalone（独立）或 genie（使用 Genie-TTS）",
    )

    parser.add_argument("--config", type=str, default=None, help="配置文件路径")

    args = parser.parse_args()

    # 如果指定了配置文件，设置环境变量
    if args.config:
        os.environ["CONFIG_FILE"] = args.config

    # 运行服务器
    if args.mode == "genie":
        run_with_genie(host=args.host, port=args.port, workers=args.workers)
    else:
        run_server(
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
            log_level=args.log_level,
        )


if __name__ == "__main__":
    main()
