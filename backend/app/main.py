"""FastAPI 应用入口 v9.0 - 团队版"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.middleware.logging import LoggingMiddleware
from app.routers import admin, auth, chat, health

# 创建应用实例
app = FastAPI(
    title="智能主板维修系统 - AI 代理服务",
    description="支持多用户、知识库管理、AI 增强诊断的团队版维修系统",
    version="9.0.0",
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
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)

# 静态文件服务 - data/ 目录
_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
if os.path.exists(_data_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/data", StaticFiles(directory=_data_dir), name="data")

# 静态文件服务 - 前端 HTML
_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_html_path = os.path.join(_root_dir, "mainboard_repair_system_v7.4_updated.html")
if os.path.exists(_html_path):
    from fastapi.responses import FileResponse

    @app.get("/")
    async def serve_index():
        return FileResponse(_html_path)

    # 也需要提供 data/ 中的 .js 文件
    js_dir = os.path.join(_root_dir, "js")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")


@app.on_event("startup")
async def startup():
    """启动时初始化数据库并打印配置"""
    # 初始化数据库
    init_db()

    settings = get_settings()
    from app.services.ai_proxy import detect_provider

    provider_id, config = detect_provider(settings.anthropic_api_key)
    print("=" * 60)
    print("  AI 代理服务器 - 智能主板维修系统 v9.0 (团队版)")
    print("=" * 60)
    print(f"  文档地址: http://localhost:{settings.port}/docs")
    print(f"  健康检查: http://localhost:{settings.port}/health")
    print(f"  登录接口: POST http://localhost:{settings.port}/auth/login")
    print(f"  API 端点: POST http://localhost:{settings.port}/api/chat")
    print("-" * 60)
    if settings.anthropic_api_key:
        print(f"  识别平台: {config['name']}")
        print(f"  默认模型: {config['default_model']}")
        print(f"  视觉分析: {'支持' if config['supports_vision'] else '不支持'}")
    else:
        print("  [WARNING] 未设置 ANTHROPIC_API_KEY")
    print("=" * 60)
