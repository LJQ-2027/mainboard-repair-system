"""速率限制测试"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


def _build_client_with_rate_limit():
    """构建启用速率限制的测试客户端"""
    # 使用独立内存数据库，避免污染主测试数据
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    db.close()


@pytest.fixture
def rl_client():
    yield from _build_client_with_rate_limit()


def _unique(name: str) -> str:
    import uuid
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
    from app.config import get_settings
    from app.middleware.rate_limit import rate_limit

    get_settings.cache_clear()
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    settings = get_settings()
    assert settings.rate_limit_enabled is True

    def sample_func(request):
        return "ok"

    wrapped = rate_limit("10/minute")(sample_func)
    # 启用时返回的被包装函数应与原函数不同
    assert wrapped is not sample_func
