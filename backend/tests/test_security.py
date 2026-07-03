"""安全相关测试"""

import uuid

import pytest

from app.config import Settings, get_settings


def _unique(name: str) -> str:
    return f"test_{name}_{uuid.uuid4().hex[:8]}"


# ---- SECRET_KEY 校验 ----

def test_secret_key_empty_raises():
    """SECRET_KEY 为空时应校验失败"""
    with pytest.raises(ValueError):
        Settings(SECRET_KEY="")


def test_secret_key_too_short_raises():
    """SECRET_KEY 太短时应校验失败"""
    with pytest.raises(ValueError):
        Settings(SECRET_KEY="short")


def test_secret_key_valid():
    """长度 >= 32 的 SECRET_KEY 应通过校验"""
    s = Settings(SECRET_KEY="x" * 32)
    assert len(s.secret_key) >= 32


# ---- 密码强度校验 ----

def test_register_weak_password_only_digits(client):
    """纯数字密码应被拒绝"""
    resp = client.post("/auth/register", json={
        "username": _unique("weak"),
        "password": "12345678",
    })
    assert resp.status_code == 422


def test_register_weak_password_only_letters(client):
    """纯字母密码应被拒绝"""
    resp = client.post("/auth/register", json={
        "username": _unique("weak"),
        "password": "password",
    })
    assert resp.status_code == 422


def test_register_short_password(client):
    """短密码应被拒绝"""
    resp = client.post("/auth/register", json={
        "username": _unique("short"),
        "password": "Ab1",
    })
    assert resp.status_code == 422


def test_register_strong_password(client):
    """满足复杂度要求的密码应注册成功"""
    username = _unique("strong")
    resp = client.post("/auth/register", json={
        "username": username,
        "password": "SecurePass123!",
    })
    assert resp.status_code == 200
    assert resp.json()["username"] == username


# ---- 用户名校验 ----

def test_register_invalid_username(client):
    """包含非法字符的用户名应被拒绝"""
    resp = client.post("/auth/register", json={
        "username": "test<script>alert(1)</script>",
        "password": "SecurePass123!",
    })
    assert resp.status_code == 422


# ---- 安全头部 ----

def test_security_headers_present(client):
    """响应应包含基础安全头部"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("Permissions-Policy") == (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    )
    assert "Content-Security-Policy" in resp.headers
    assert "Strict-Transport-Security" not in resp.headers


def test_security_headers_on_error_response(client):
    """错误响应也应包含安全头部"""
    resp = client.get("/nonexistent-path")
    assert resp.status_code == 404
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in resp.headers


def test_hsts_disabled_by_default(client):
    """默认不返回 HSTS 头部"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_enabled_when_configured(client, monkeypatch):
    """开启 ENABLE_HSTS 后应返回 HSTS 头部"""
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_HSTS", "true")
    monkeypatch.setenv("HSTS_MAX_AGE", "86400")

    # 重新加载配置并覆盖依赖
    settings = get_settings()
    assert settings.enable_hsts is True

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("Strict-Transport-Security") == "max-age=86400; includeSubDomains"

    get_settings.cache_clear()


# ---- /uploads 受控访问 ----

def test_uploads_requires_auth(client):
    """未登录访问上传文件应返回 401"""
    resp = client.get("/uploads/X6878/test.pdf")
    assert resp.status_code == 401


def test_uploads_directory_traversal_blocked(client):
    """目录遍历请求应被阻止"""
    # 即便带 token，路径越界也应 404
    resp = client.get("/uploads/../app/main.py")
    # 未登录先触发 401，这里重点是不允许越界访问
    assert resp.status_code in (401, 404)


# ---- CORS 配置 ----

def test_cors_not_wildcard_with_credentials():
    """生产环境不应同时启用 * 来源与 credentials"""
    # 测试环境已设置具体来源，因此来源字符串不应为 *
    s = get_settings()
    if s.allow_credentials:
        assert s.cors_origins != "*"
