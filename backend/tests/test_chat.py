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


def test_structured_chat_saves_parsed_result(client, db_session, monkeypatch):
    """结构化诊断请求会解析并保存 JSON 结果"""
    username = _unique("structured")
    client.post("/auth/register", json={"username": username, "password": "SecurePass123!"})
    login = client.post("/auth/login", json={"username": username, "password": "SecurePass123!"})
    token = login.json()["access_token"]

    async def fake_chat_sync(payload, api_key_override=None, provider_override=None):
        return {
            "content": [{
                "type": "text",
                "text": (
                    "建议更换电源IC。\n\n"
                    "```json\n"
                    '{"fault_type": "不开机", "confidence": "high", "summary": "电源IC损坏"}\n'
                    "```"
                ),
            }]
        }

    monkeypatch.setattr("app.services.chat_service.chat_sync", fake_chat_sync)

    resp = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "messages": [{"role": "user", "content": "手机不开机"}],
            "stream": False,
            "structured": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "电源IC" in data["content"][0]["text"]
    assert "```json" not in data["content"][0]["text"]

    # 查询历史详情验证结构化结果
    history = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    record_id = history.json()[0]["id"]

    detail = client.get(
        f"/api/history/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["structured_result"]["fault_type"] == "不开机"
    assert detail_data["structured_result"]["confidence"] == "high"


def test_history_detail_not_found(client, db_session):
    """查询不存在的诊断记录返回 404"""
    username = _unique("histdetail")
    client.post("/auth/register", json={"username": username, "password": "SecurePass123!"})
    login = client.post("/auth/login", json={"username": username, "password": "SecurePass123!"})
    token = login.json()["access_token"]

    resp = client.get("/api/history/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_history_detail_forbidden(client, db_session):
    """用户不能查看他人的诊断记录"""
    user1 = _unique("user1")
    user2 = _unique("user2")
    client.post("/auth/register", json={"username": user1, "password": "SecurePass123!"})
    client.post("/auth/register", json={"username": user2, "password": "SecurePass123!"})

    login1 = client.post("/auth/login", json={"username": user1, "password": "SecurePass123!"})
    token1 = login1.json()["access_token"]

    login2 = client.post("/auth/login", json={"username": user2, "password": "SecurePass123!"})
    token2 = login2.json()["access_token"]

    # 用 user1 创建一条诊断记录
    from app.models.diagnosis import DiagnosisRecord
    from app.models.user import User
    user = db_session.query(User).filter(User.username == user1).first()
    record = DiagnosisRecord(
        user_id=user.id,
        mode="AI",
        symptom="test",
        project_model="X6878",
    )
    db_session.add(record)
    db_session.commit()
    record_id = record.id

    # user2 访问应 404（不暴露存在性）
    resp = client.get(
        f"/api/history/{record_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404
