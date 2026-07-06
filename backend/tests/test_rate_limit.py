"""速率限制测试"""

import uuid

from app.config import get_settings


def _unique(name: str) -> str:
    return f"test_{name}_{uuid.uuid4().hex[:8]}"


def test_rate_limit_disabled_in_tests(client):
    """测试环境默认关闭限流，多次注册不应被限制"""
    for i in range(6):
        resp = client.post("/auth/register", json={
            "username": _unique(f"nolimit{i}"),
            "password": "SecurePass123!",
        })
        assert resp.status_code == 200, f"第 {i} 次注册应成功"


def test_rate_limit_applies_when_enabled(monkeypatch):
    """启用限流时，rate_limit 装饰器会对函数进行包装"""
    get_settings.cache_clear()
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    settings = get_settings()
    assert settings.rate_limit_enabled is True

    from app.middleware.rate_limit import rate_limit

    def sample_func(request):
        return "ok"

    wrapped = rate_limit("10/minute")(sample_func)
    # 启用时返回的被包装函数应与原函数不同
    assert wrapped is not sample_func
