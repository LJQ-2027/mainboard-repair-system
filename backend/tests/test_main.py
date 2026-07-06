"""应用启动测试"""

import pytest


def test_startup_handles_missing_api_key(monkeypatch):
    """未配置 API Key 时启动不应崩溃"""
    from app.main import lifespan

    def fake_init_db():
        pass

    def fake_get_settings():
        class FakeSettings:
            anthropic_api_key = ""
            port = 8899

        return FakeSettings()

    monkeypatch.setattr("app.main.init_db", fake_init_db)
    monkeypatch.setattr("app.main.get_settings", fake_get_settings)

    # 不应抛出异常
    import asyncio
    asyncio.run(_run_lifespan(lifespan))


def test_startup_handles_unrecognized_api_key(monkeypatch):
    """API Key 无法识别时启动不应崩溃"""
    from app.main import lifespan
    from fastapi import HTTPException

    def fake_init_db():
        pass

    def fake_detect_provider(api_key):
        raise HTTPException(status_code=400, detail="无法识别")

    def fake_get_settings():
        class FakeSettings:
            anthropic_api_key = "invalid-key"
            port = 8899

        return FakeSettings()

    monkeypatch.setattr("app.main.init_db", fake_init_db)
    monkeypatch.setattr("app.main.get_settings", fake_get_settings)
    monkeypatch.setattr("app.services.ai_proxy.detect_provider", fake_detect_provider)

    # 不应抛出异常
    import asyncio
    asyncio.run(_run_lifespan(lifespan))


def _run_lifespan(lifespan):
    """辅助函数：运行 lifespan 的 startup 部分"""
    async def _inner():
        async with lifespan(None):
            pass
    return _inner()
