"""请求日志中间件"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.logging_config import get_logger

logger = get_logger("mainboard-repair")


class LoggingMiddleware(BaseHTTPMiddleware):
    """记录每次请求的耗时、方法、状态码"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        response = await call_next(request)

        duration = (time.time() - start) * 1000
        status = response.status_code

        log_data = {
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": round(duration, 1),
            "client": client,
        }

        # 同时兼容 structlog 与标准库 logging：使用 extra 传递结构化字段
        if status >= 500:
            logger.error("request", extra=log_data)
        elif status >= 400:
            logger.warning("request", extra=log_data)
        else:
            logger.info("request", extra=log_data)

        return response
