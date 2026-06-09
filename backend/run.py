#!/usr/bin/env python3
"""FastAPI 代理服务启动脚本

用法:
    python run.py              # 默认启动
    python run.py --port 8899  # 指定端口
    python run.py --reload     # 开发模式（自动重载）
"""

import argparse

import uvicorn

from app.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="智能主板维修系统 - AI 代理服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="监听端口 (默认: .env 中 PORT 或 8899)")
    parser.add_argument("--reload", action="store_true", help="开发模式：代码变更自动重载")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")
    args = parser.parse_args()

    settings = get_settings()
    port = args.port or settings.port

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
