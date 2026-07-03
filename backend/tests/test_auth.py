"""认证服务单元测试"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.user import User


def _unique(name: str) -> str:
    return f"test_{name}_{uuid.uuid4().hex[:8]}"


def test_register_new_user(client):
    resp = client.post("/auth/register", json={
        "username": _unique("reg"), "password": "SecurePass123!"
    })
    assert resp.status_code == 200
    assert resp.json()["username"].startswith("test_reg")


def test_register_duplicate(client):
    username = _unique("dup")
    client.post("/auth/register", json={"username": username, "password": "SecurePass123!"})
    resp = client.post("/auth/register", json={"username": username, "password": "SecurePass123!"})
    assert resp.status_code == 400


def test_login_valid(client):
    username = _unique("login")
    client.post("/auth/register", json={"username": username, "password": "MyPass123!"})
    resp = client.post("/auth/login", json={"username": username, "password": "MyPass123!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    username = _unique("wrong")
    client.post("/auth/register", json={"username": username, "password": "Correct123!"})
    resp = client.post("/auth/login", json={"username": username, "password": "WRONG"})
    assert resp.status_code == 401


def test_me_endpoint(client):
    username = _unique("me")
    client.post("/auth/register", json={"username": username, "password": "SecurePass123!"})
    login = client.post("/auth/login", json={"username": username, "password": "SecurePass123!"})
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == username


def test_me_no_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_admin_access(client, db_session: Session):
    username = _unique("admin")
    client.post("/auth/register", json={"username": username, "password": "Admin123!"})
    login = client.post("/auth/login", json={"username": username, "password": "Admin123!"})
    token = login.json()["access_token"]

    # 升级权限
    user = db_session.query(User).filter(User.username == username).first()
    user.role = "admin"
    db_session.commit()

    resp = client.get("/admin/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_normal_user_cannot_access_admin(client):
    """普通用户不能执行需要管理员权限的操作"""
    username = _unique("normal")
    client.post("/auth/register", json={"username": username, "password": "UserPass123!"})
    login = client.post("/auth/login", json={"username": username, "password": "UserPass123!"})
    token = login.json()["access_token"]
    # 删除知识库需要管理员权限
    resp = client.get("/admin/knowledge/1/delete", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
