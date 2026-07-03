"""FastAPI 应用入口 v9.0 - 团队版"""

import mimetypes
import os
import re

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.middleware.logging import LoggingMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.routers import admin, auth, chat, health
from app.services.auth import get_current_user

# 创建应用实例
app = FastAPI(
    title="智能主板维修系统 - AI 代理服务",
    description="支持多用户、知识库管理、AI 增强诊断的团队版维修系统",
    version="9.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件（来源从配置读取，避免 allow_origins=["*"] 与 allow_credentials=True 同时存在）
settings = get_settings()
_cors_origins = settings.get_cors_origins()
if _cors_origins == ["*"] and settings.allow_credentials:
    import logging
    _cors_logger = logging.getLogger("mainboard-repair")
    _cors_logger.warning(
        "CORS allow_origins=['*'] 与 allow_credentials=True 同时启用，"
        "浏览器会拒绝携带 Cookie。生产环境请在 .env 中设置 CORS_ORIGINS。"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)

# 安全头部中间件
app.add_middleware(SecurityHeadersMiddleware)

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
    app.mount("/data", StaticFiles(directory=_data_dir), name="data")

# 静态文件服务 - 前端 HTML
_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_html_path = os.path.join(_root_dir, "mainboard_repair_system_v7.4_updated.html")
if os.path.exists(_html_path):
    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        with open(_html_path, "r", encoding="utf-8") as f:
            html = f.read()
        return Response(content=html, media_type="text/html",
                       headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                                "Pragma": "no-cache", "Expires": "0"})

    # 也需要提供 data/ 中的 .js 文件
    js_dir = os.path.join(_root_dir, "js")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

    # 新版 Vite 前端构建产物（挂载在 /v2/，保留旧版 / 入口）
    frontend_dist = os.path.join(_root_dir, "frontend", "dist")
    if os.path.exists(frontend_dist):
        app.mount("/v2", StaticFiles(directory=frontend_dist, html=True), name="frontend_v2")

# 本地上传文件目录
_uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(_uploads_dir, exist_ok=True)

# 受控的上传文件访问路由（替代直接静态挂载，防止任意文件执行与目录遍历）
_allowed_upload_exts = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}


@app.get("/uploads/{project_code}/{filename}")
async def serve_upload(
    project_code: str,
    filename: str,
    user=Depends(get_current_user),
):
    """受控的文件访问 - 仅允许已登录用户访问指定类型的项目资料"""
    # 净化参数
    safe_project = re.sub(r"[^\w\-]", "", project_code)
    safe_filename = os.path.basename(filename)

    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in _allowed_upload_exts:
        raise HTTPException(status_code=403, detail="不支持的文件类型")

    # 构建路径并校验目录遍历
    file_path = os.path.join(_uploads_dir, safe_project, safe_filename)
    real_path = os.path.realpath(file_path)
    real_uploads = os.path.realpath(_uploads_dir)
    if not real_path.startswith(real_uploads) or not os.path.isfile(real_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    media_type, _ = mimetypes.guess_type(real_path)
    with open(real_path, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type=media_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename={safe_filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
