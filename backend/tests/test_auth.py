"""认证服务单元测试"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User


def _unique(name: str) -> str:
    return f"test_{name}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client():
    return TestClient(app)


def test_register_new_user(client):
    resp = client.post("/auth/register", json={
        "username": _unique("reg"), "password": "secure123"
    })
    assert resp.status_code == 200
    assert resp.json()["username"].startswith("test_reg")


def test_register_duplicate(client):
    username = _unique("dup")
    client.post("/auth/register", json={"username": username, "password": "pass123"})
    resp = client.post("/auth/register", json={"username": username, "password": "pass123"})
    assert resp.status_code == 400


def test_login_valid(client):
    username = _unique("login")
    client.post("/auth/register", json={"username": username, "password": "mypass"})
    resp = client.post("/auth/login", json={"username": username, "password": "mypass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    username = _unique("wrong")
    client.post("/auth/register", json={"username": username, "password": "correct"})
    resp = client.post("/auth/login", json={"username": username, "password": "WRONG"})
    assert resp.status_code == 401


def test_me_endpoint(client):
    username = _unique("me")
    client.post("/auth/register", json={"username": username, "password": "pass"})
    login = client.post("/auth/login", json={"username": username, "password": "pass"})
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == username


def test_me_no_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_admin_access(client):
    db = SessionLocal()
    try:
        username = _unique("admin")
        client.post("/auth/register", json={"username": username, "password": "admin123"})
        login = client.post("/auth/login", json={"username": username, "password": "admin123"})
        token = login.json()["access_token"]

        # 升级权限
        user = db.query(User).filter(User.username == username).first()
        user.role = "admin"
        db.commit()

        resp = client.get("/admin/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
    finally:
        db.rollback()
        db.close()


def test_normal_user_cannot_access_admin(client):
    username = _unique("normal")
    client.post("/auth/register", json={"username": username, "password": "pass"})
    login = client.post("/auth/login", json={"username": username, "password": "pass"})
    token = login.json()["access_token"]
    resp = client.get("/admin/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
