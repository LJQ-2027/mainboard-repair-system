"""健康检查路由"""

import os
import shutil

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database import DB_PATH, SQLALCHEMY_DATABASE_URL, engine
from app.services.ai_proxy import get_health_info

router = APIRouter(tags=["health"])


def _check_database() -> dict[str, str]:
    """检查数据库连通性"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_type = "sqlite" if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else "postgresql"
        return {"status": "ok", "type": db_type}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_disk() -> dict[str, str | float | bool]:
    """检查数据目录磁盘空间（仅 SQLite 模式）"""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite") or not DB_PATH:
        return {"status": "n/a"}

    try:
        data_dir = os.path.dirname(DB_PATH)
        usage = shutil.disk_usage(data_dir)
        free_gb = round(usage.free / (1024 ** 3), 2)
        return {
            "status": "warning" if free_gb < 1 else "ok",
            "free_gb": free_gb,
        }
    except Exception as e:
        return {"status": "unknown", "detail": str(e)}


@router.get("/health")
async def health_check():
    """代理服务器健康检查 - 包含 AI 配置、数据库、磁盘状态"""
    result = {
        "status": "ok",
        "version": "9.0.0",
    }

    # AI 配置状态
    result["ai"] = get_health_info()

    # 数据库连接检查
    result["database"] = _check_database()

    # 磁盘空间检查
    result["disk"] = _check_disk()

    # 任一关键组件异常则返回 503
    if result["database"]["status"] == "error":
        result["status"] = "degraded"
        raise HTTPException(status_code=503, detail=result)

    return result
