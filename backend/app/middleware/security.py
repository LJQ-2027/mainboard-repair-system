"""安全响应头部中间件

为所有响应添加基础安全头部，降低常见 Web 攻击风险：
- 点击劫持
- MIME 嗅探
- XSS
- 不安全来源/混合内容

HSTS 默认关闭，仅在确认通过 HTTPS 提供服务时于 .env 中开启。
"""

from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应添加基础安全头部"""

    # CSP：仅在必要时允许 unsafe-inline。
    # 如果新版 Vite 前端不再需要内联脚本/样式，可进一步移除 unsafe-inline。
    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "frame-ancestors 'none';"
        "base-uri 'self';"
        "form-action 'self';"
    )

    _PERMISSIONS_POLICY = (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并附加安全头部

        即使下游处理异常，也会尝试附加头部，避免泄漏无头部响应。
        """
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001
            # 中间件不应吞掉异常，但须确保在可能的响应对象上附加头部
            raise

        self._add_headers(response)
        return response

    def _add_headers(self, response: Response) -> None:
        """为响应对象添加安全头部"""
        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # 禁止 MIME 类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS 保护（旧浏览器兜底）
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 内容安全策略
        response.headers["Content-Security-Policy"] = self._CSP

        # 引用策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略（限制浏览器功能）
        response.headers["Permissions-Policy"] = self._PERMISSIONS_POLICY

        # HTTP Strict Transport Security（仅在明确开启时添加）
        settings = get_settings()
        if settings.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.hsts_max_age}; includeSubDomains"
            )
