"""请求日志中间件 - 支持文件轮转"""

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ---- 日志配置 ----
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server.log")

# 配置 logger
logger = logging.getLogger("mainboard-repair")
logger.setLevel(logging.INFO)

# 仅在 logger 没有 handler 时注册，避免热重载/多 worker 重复追加
if not logger.handlers:
    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(console)

    # 文件轮转：单文件最大 10MB，保留 5 个备份
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)


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

        msg = f"{method} {path} | {status} | {duration:.1f}ms | {client}"

        if status >= 500:
            logger.error(msg)
        elif status >= 400:
            logger.warning(msg)
        else:
            logger.info(msg)

        return response
