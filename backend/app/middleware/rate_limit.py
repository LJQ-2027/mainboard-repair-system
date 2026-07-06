"""速率限制中间件

基于 SlowAPI，按用户（已登录）或 IP（匿名）限流。
"""

from functools import wraps

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.services.auth import decode_token


class RateLimitKeyMiddleware(BaseHTTPMiddleware):
    """在请求状态上设置 rate_limit_key，供 SlowAPI 使用"""

    async def dispatch(self, request: Request, call_next):
        key = self._resolve_key(request)
        request.state.rate_limit_key = key
        return await call_next(request)

    def _resolve_key(self, request: Request) -> str:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            payload = decode_token(token)
            if payload and isinstance(payload, dict):
                username = payload.get("sub")
                if username:
                    return f"user:{username}"
        return f"ip:{get_remote_address(request)}"


def _rate_limit_key(request: Request) -> str:
    """SlowAPI key function"""
    return getattr(request.state, "rate_limit_key", f"ip:{get_remote_address(request)}")


# 默认限流：所有接口 100 次/分钟
_limiter = Limiter(key_func=_rate_limit_key, default_limits=["100/minute"])


def rate_limit(limit_value: str):
    """速率限制装饰器

    根据 RATE_LIMIT_ENABLED 配置决定是否启用。便于测试环境关闭限流。
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        def _noop(func):
            return func
        return _noop

    def _decorator(func):
        return _limiter.limit(limit_value)(func)
    return _decorator


def get_limiter() -> Limiter:
    """返回 SlowAPI Limiter 实例，用于 FastAPI 状态注册"""
    return _limiter
