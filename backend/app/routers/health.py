"""健康检查路由"""

from fastapi import APIRouter

from app.services.ai_proxy import get_health_info

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """代理服务器健康检查"""
    return get_health_info()
