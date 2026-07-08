"""Prometheus 指标中间件

收集基础 HTTP 请求指标和 AI 调用指标。
未安装 prometheus-client 时自动禁用。
"""

import time
from typing import Callable

try:
    from fastapi import Request, Response
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
    from starlette.middleware.base import BaseHTTPMiddleware

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    Request = None  # type: ignore
    Response = None  # type: ignore
    BaseHTTPMiddleware = None  # type: ignore


if _PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )

    REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    AI_CALL_COUNT = Counter(
        "ai_calls_total",
        "Total AI API calls",
        ["provider", "status"],
    )

    AI_CALL_DURATION = Histogram(
        "ai_call_duration_seconds",
        "AI API call duration in seconds",
        ["provider"],
        buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 180.0],
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    """收集 HTTP 请求指标"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        method = request.method
        endpoint = request.url.path
        status_code = str(response.status_code)

        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return response


def is_metrics_available() -> bool:
    return _PROMETHEUS_AVAILABLE


def get_metrics():
    """生成 Prometheus 指标数据"""
    if not _PROMETHEUS_AVAILABLE:
        return b"# metrics disabled: prometheus-client not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST


def record_ai_call(provider: str, duration: float, success: bool) -> None:
    """记录 AI 调用指标"""
    if not _PROMETHEUS_AVAILABLE:
        return
    status = "success" if success else "error"
    AI_CALL_COUNT.labels(provider=provider, status=status).inc()
    AI_CALL_DURATION.labels(provider=provider).observe(duration)
