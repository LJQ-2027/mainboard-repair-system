"""Sentry 集成

可选错误追踪，仅在 SENTRY_DSN 配置时启用。
"""

from app.config import Settings


def init_sentry(settings: Settings) -> None:
    """初始化 Sentry SDK（如果配置了 DSN）"""
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )
    except ImportError:
        import logging

        logging.getLogger("mainboard-repair").warning(
            "SENTRY_DSN 已配置但 sentry-sdk 未安装，跳过 Sentry 初始化"
        )
