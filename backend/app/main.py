"""FastAPI 应用入口"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.logging import LoggingMiddleware
from app.routers import chat, health

# 创建应用实例
app = FastAPI(
    title="智能主板维修系统 - AI 代理服务",
    description="支持 Kimi / Anthropic Claude / DeepSeek 多平台的 AI 代理",
    version="8.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
app.add_middleware(LoggingMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(chat.router)

# 静态文件服务 - data/ 目录
_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
if os.path.exists(_data_dir):
    from fastapi.staticfiles import StaticFiles

    app.mount("/data", StaticFiles(directory=_data_dir), name="data")


@app.on_event("startup")
async def startup():
    """启动时打印配置信息"""
    settings = get_settings()
    from app.services.ai_proxy import detect_provider

    provider_id, config = detect_provider(settings.anthropic_api_key)
    print("=" * 60)
    print("  AI 代理服务器 - 智能主板维修系统 v8.2 (FastAPI)")
    print("=" * 60)
    print(f"  文档地址: http://localhost:{settings.port}/docs")
    print(f"  健康检查: http://localhost:{settings.port}/health")
    print(f"  API 端点: POST http://localhost:{settings.port}/api/chat")
    print("-" * 60)
    if settings.anthropic_api_key:
        print(f"  识别平台: {config['name']}")
        print(f"  默认模型: {config['default_model']}")
        print(f"  视觉分析: {'支持' if config['supports_vision'] else '不支持'}")
    else:
        print("  [WARNING] 未设置 ANTHROPIC_API_KEY")
    print("=" * 60)
