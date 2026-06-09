"""请求日志中间件"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """记录每次请求的耗时和方法"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        response = await call_next(request)

        duration = (time.time() - start) * 1000
        status = response.status_code

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {method} {path} | {status} | {duration:.1f}ms | {client}")

        return response
