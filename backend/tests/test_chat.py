"""聊天路由测试"""

import uuid

import pytest


def _unique(name: str) -> str:
    return f"test_{name}_{uuid.uuid4().hex[:8]}"


def test_chat_schema_rejects_empty_messages(client):
    """空 messages 应被 Schema 拒绝"""
    resp = client.post("/api/chat", json={"messages": [], "stream": False})
    assert resp.status_code == 422


def test_chat_schema_rejects_missing_messages(client):
    """缺少 messages 字段应被 Schema 拒绝"""
    resp = client.post("/api/chat", json={"stream": False})
    assert resp.status_code == 422


def test_chat_system_prompt_too_long(client):
    """过长的 system prompt 应被拒绝"""
    resp = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "test"}],
        "system": "x" * 10001,
        "stream": False,
    })
    assert resp.status_code == 400


def test_chat_invalid_symptom(client):
    """包含非法内容的故障现象应被拒绝"""
    resp = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "<script>alert(1)</script>"}],
        "stream": False,
    })
    assert resp.status_code == 400


def test_create_session_requires_auth(client):
    """创建会话需要登录"""
    resp = client.post("/api/chat/sessions")
    assert resp.status_code == 401


def test_list_sessions_requires_auth(client):
    """列会话需要登录"""
    resp = client.get("/api/chat/sessions")
    assert resp.status_code == 401


def test_history_requires_auth(client):
    """历史记录需要登录"""
    resp = client.get("/api/history")
    assert resp.status_code == 401


def test_create_and_list_session(client, db_session):
    """登录用户可以创建和列会话"""
    username = _unique("session")
    client.post("/auth/register", json={"username": username, "password": "SecurePass123!"})
    login = client.post("/auth/login", json={"username": username, "password": "SecurePass123!"})
    token = login.json()["access_token"]

    create_resp = client.post("/api/chat/sessions", headers={"Authorization": f"Bearer {token}"})
    assert create_resp.status_code == 200
    session_id = create_resp.json()["id"]

    list_resp = client.get("/api/chat/sessions", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert any(s["id"] == session_id for s in list_resp.json())
