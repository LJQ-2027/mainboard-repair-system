"""聊天业务逻辑服务测试"""

import json

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisRecord
from app.models.session import ChatSession
from app.models.user import User
from app.services.chat_service import (
    build_chat_payload,
    build_mode_from_system,
    execute_chat_sync,
    get_content_preview,
    get_last_message_content,
    get_request_messages,
    is_text_content,
    load_session_history,
    prepare_chat_context,
    save_diagnosis_record,
    update_diagnosis_result,
    update_session,
    validate_and_prepare_request,
)


def test_get_last_message_content_text():
    messages = [{"role": "user", "content": "手机不开机"}]
    assert get_last_message_content(messages) == "手机不开机"


def test_get_last_message_content_image():
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "分析"}]}]
    content = get_last_message_content(messages)
    assert isinstance(content, list)


def test_get_last_message_content_empty():
    assert get_last_message_content([]) == ""


def test_is_text_content():
    assert is_text_content("hello") is True
    assert is_text_content([{"type": "image"}]) is False


def test_get_content_preview():
    assert get_content_preview("1234567890", max_len=5) == "12345"
    assert get_content_preview([{"type": "image"}]) == "图片分析"


def test_build_mode_from_system():
    assert build_mode_from_system("AI 智能诊断") == "AI"
    assert build_mode_from_system("一般对话") == "对话"


def test_save_diagnosis_record(db_session: Session):
    user = User(username="chat_test_user", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    record = save_diagnosis_record(
        db_session, user, "AI", "手机不开机", "kimi-k2", "X6878", False
    )
    assert record.id is not None
    assert record.user_id == user.id
    assert record.mode == "AI"


def test_update_diagnosis_result(db_session: Session):
    user = User(username="chat_test_user2", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    record = save_diagnosis_record(db_session, user, "AI", "test", "", "", False)
    result = {"content": [{"type": "text", "text": "建议检查电源IC"}]}
    update_diagnosis_result(db_session, record, result)
    assert record.result_text == "建议检查电源IC"


def test_load_session_history(db_session: Session):
    user = User(username="chat_test_user3", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    session = ChatSession(
        user_id=user.id,
        messages_json=json.dumps([{"role": "user", "content": "历史"}]),
    )
    db_session.add(session)
    db_session.commit()

    found, merged = load_session_history(
        db_session, session.id, user.id, [{"role": "user", "content": "新消息"}]
    )
    assert found is not None
    assert len(merged) == 2


def test_load_session_history_not_found(db_session: Session):
    user = User(username="chat_test_user4", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    found, merged = load_session_history(
        db_session, 99999, user.id, [{"role": "user", "content": "新消息"}]
    )
    assert found is None
    assert len(merged) == 1


def test_update_session(db_session: Session):
    user = User(username="chat_test_user5", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    update_session(db_session, session, [{"role": "user", "content": "新会话标题内容"}])
    assert session.title == "新会话标题内容"
    assert "新会话标题内容" in session.messages_json


def test_update_session_keeps_title_with_history(db_session: Session):
    """合并历史后不应覆盖已有标题"""
    user = User(username="chat_test_user6", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    session = ChatSession(user_id=user.id, title="已有标题")
    db_session.add(session)
    db_session.commit()

    update_session(
        db_session,
        session,
        [
            {"role": "user", "content": "历史1"},
            {"role": "assistant", "content": "回复"},
            {"role": "user", "content": "新消息"},
        ],
    )
    assert session.title == "已有标题"


def test_validate_and_prepare_request_adds_citation():
    from app.schemas.chat import ChatRequest

    request = ChatRequest(messages=[{"role": "user", "content": "test"}], system="主板维修助手")
    result = validate_and_prepare_request(request)
    assert "引用" in result.system


def test_validate_and_prepare_request_already_has_citation():
    from app.schemas.chat import ChatRequest

    system = "主板维修助手\n\n## 引用\n- [知识库]"
    request = ChatRequest(messages=[{"role": "user", "content": "test"}], system=system)
    result = validate_and_prepare_request(request)
    assert result.system == system


def test_validate_and_prepare_request_rejects_long_system():
    from app.schemas.chat import ChatRequest

    request = ChatRequest(messages=[{"role": "user", "content": "test"}], system="x" * 10001)

    with pytest.raises(HTTPException) as exc_info:
        validate_and_prepare_request(request)
    assert exc_info.value.status_code == 400


def test_get_request_messages_sanitizes_text():
    from app.schemas.chat import ChatRequest

    request = ChatRequest(messages=[{"role": "user", "content": "  手机不开机  "}])
    messages, last_content = get_request_messages(request)
    assert last_content == "手机不开机"
    assert messages[-1]["content"] == "手机不开机"


def test_get_request_messages_rejects_invalid_symptom():
    from app.schemas.chat import ChatRequest

    request = ChatRequest(messages=[{"role": "user", "content": "<script>alert(1)</script>"}])

    with pytest.raises(HTTPException) as exc_info:
        get_request_messages(request)
    assert exc_info.value.status_code == 400


def test_build_chat_payload():
    from app.schemas.chat import ChatRequest

    request = ChatRequest(
        messages=[{"role": "user", "content": "test"}],
        system="助手",
        model="kimi-k2",
        max_tokens=1024,
        temperature=0.5,
        stream=False,
        project="X6878",
    )
    messages = [{"role": "user", "content": "test"}]
    payload = build_chat_payload(request, messages)
    assert payload["model"] == "kimi-k2"
    assert payload["system"] == "助手"
    assert payload["messages"] == messages
    assert payload["max_tokens"] == 1024
    assert payload["temperature"] == 0.5
    assert payload["stream"] is False


def test_prepare_chat_context_anonymous():
    from app.schemas.chat import ChatRequest

    request = ChatRequest(messages=[{"role": "user", "content": "test"}])
    messages = [{"role": "user", "content": "test"}]
    session, diagnosis, merged = prepare_chat_context(None, None, request, messages, "test")
    assert session is None
    assert diagnosis is None
    assert merged == messages


def test_prepare_chat_context_logged_in(db_session: Session):
    user = User(username="chat_test_user7", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    from app.schemas.chat import ChatRequest

    request = ChatRequest(messages=[{"role": "user", "content": "手机不开机"}], project="X6878")
    messages = [{"role": "user", "content": "手机不开机"}]
    session, diagnosis, merged = prepare_chat_context(
        db_session, user, request, messages, "手机不开机"
    )
    assert session is None
    assert diagnosis is not None
    assert diagnosis.user_id == user.id
    assert diagnosis.symptom == "手机不开机"
    assert diagnosis.project_model == "X6878"
    assert merged == messages


@pytest.mark.anyio
async def test_execute_chat_sync_updates_diagnosis(db_session: Session, monkeypatch):
    user = User(username="chat_test_user8", hashed_password="fake")
    db_session.add(user)
    db_session.commit()

    from app.schemas.chat import ChatRequest

    request = ChatRequest(
        messages=[{"role": "user", "content": "手机不开机"}],
        stream=False,
        system="AI 智能诊断",
    )

    async def fake_chat_sync(payload, api_key_override=None, provider_override=None):
        return {"content": [{"type": "text", "text": "建议检查电源IC"}]}

    monkeypatch.setattr("app.services.chat_service.chat_sync", fake_chat_sync)
    result = await execute_chat_sync(db_session, user, request)
    assert result["content"][0]["text"] == "建议检查电源IC"

    records = db_session.query(DiagnosisRecord).filter(DiagnosisRecord.user_id == user.id).all()
    assert len(records) == 1
    assert records[0].result_text == "建议检查电源IC"


@pytest.mark.anyio
async def test_safe_stream_generator_handles_http_exception(monkeypatch):
    from app.services.chat_service import _safe_stream_generator

    async def failing_stream(payload, api_key_override=None, provider_override=None):
        raise HTTPException(status_code=429, detail="请求过于频繁")
        yield ""

    monkeypatch.setattr("app.services.chat_service.stream_chat", failing_stream)
    chunks = []
    async for chunk in _safe_stream_generator({}):
        chunks.append(chunk)
    assert len(chunks) == 1
    assert "请求过于频繁" in chunks[0]
