"""健康检查路由"""

import os
import shutil
import sqlite3

from fastapi import APIRouter, HTTPException

from app.database import DB_PATH
from app.services.ai_proxy import get_health_info

router = APIRouter(tags=["health"])


def _check_database() -> dict[str, str]:
    """检查 SQLite 数据库连通性"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=2)
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_disk() -> dict[str, str | float | bool]:
    """检查数据目录磁盘空间"""
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

    # AI 配置状态（已有）
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
