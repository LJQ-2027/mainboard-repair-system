"""聊天业务逻辑服务

将 AI 对话的核心流程（输入校验、会话历史、诊断记录、AI 调用）从路由层抽离，
便于单独测试和复用。
"""

import json
from typing import Any, AsyncGenerator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisRecord
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.ai_proxy import chat_sync, stream_chat
from app.utils.validators import sanitize_input, validate_symptom, validate_system_prompt

# 当 system prompt 涉及维修但未要求引用时，自动追加引用提示
_CITATION_PROMPT = (
    "\n\n## 重要：请在你的回复中标注引用来源\n"
    "- 如果参考了知识库信息，用 [知识库: 标题] 标注\n"
    "- 如果参考了本地案例，用 [案例: 故障类型] 标注\n"
    "- 如果是基于专业经验，用 [经验] 标注"
)


def get_last_message_content(messages: list[dict[str, Any]]) -> Any:
    """安全获取最后一条消息的内容"""
    if not messages:
        return ""
    last = messages[-1]
    return last.get("content", "") if isinstance(last, dict) else ""


def is_text_content(content: Any) -> bool:
    """判断内容是否为纯文本"""
    return isinstance(content, str)


def get_content_preview(content: Any, max_len: int = 50) -> str:
    """获取内容预览（用于会话标题）"""
    if isinstance(content, str):
        return content[:max_len]
    return "图片分析"


def build_mode_from_system(system: str) -> str:
    """根据 system prompt 判断诊断模式"""
    return "AI" if "AI 智能诊断" in system else "对话"


def validate_and_prepare_request(request: ChatRequest) -> ChatRequest:
    """校验并准备请求：system prompt、引用提示、基本参数"""
    if request.system:
        ok, err = validate_system_prompt(request.system)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        if "引用" not in request.system and "维修" in request.system:
            request.system += _CITATION_PROMPT
    return request


def get_request_messages(request: ChatRequest) -> tuple[list[dict[str, Any]], Any]:
    """提取并净化请求消息，返回 (messages, last_content)

    仅对最后一条文本消息进行长度、敏感词校验和净化。
    """
    messages = [m.model_dump() for m in request.messages]
    last_content = get_last_message_content(messages)

    if is_text_content(last_content) and last_content:
        ok, err = validate_symptom(last_content)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        sanitized = sanitize_input(last_content)
        messages[-1]["content"] = sanitized
        last_content = sanitized

    return messages, last_content


def build_chat_payload(
    request: ChatRequest, messages: list[dict[str, Any]]
) -> dict[str, Any]:
    """根据 ChatRequest 构建传给 AI 代理的 payload"""
    return {
        "model": request.model,
        "system": request.system,
        "messages": messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "stream": request.stream,
    }


def save_diagnosis_record(
    db: Session,
    user: User,
    mode: str,
    symptom: str,
    ai_model: str,
    project_model: str,
    has_image: bool,
) -> DiagnosisRecord:
    """保存诊断记录"""
    diagnosis = DiagnosisRecord(
        user_id=user.id,
        mode=mode,
        symptom=symptom,
        ai_model=ai_model,
        project_model=project_model,
        has_image=has_image,
        result_text="",
    )
    db.add(diagnosis)
    db.commit()
    return diagnosis


def update_diagnosis_result(
    db: Session,
    diagnosis: DiagnosisRecord,
    result: dict[str, Any],
) -> None:
    """更新诊断结果"""
    text = ""
    if isinstance(result, dict) and "content" in result:
        for block in result.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")
    diagnosis.result_text = text
    db.commit()


def load_session_history(
    db: Session,
    session_id: int | None,
    user_id: int,
    current_messages: list[dict[str, Any]],
) -> tuple[ChatSession | None, list[dict[str, Any]]]:
    """加载会话历史并合并当前消息"""
    if not session_id:
        return None, current_messages

    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    ).first()
    if session:
        history = json.loads(session.messages_json)
        merged = history[-10:] + current_messages
        return session, merged
    return None, current_messages


def update_session(
    db: Session,
    session: ChatSession,
    messages: list[dict[str, Any]],
) -> None:
    """更新会话消息和标题

    标题仅在仍为默认值时，从第一条用户消息提取，避免合并历史后覆盖。
    """
    session.messages_json = json.dumps(messages, ensure_ascii=False)
    if session.title == "新会话":
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                session.title = get_content_preview(content)
                break
    db.commit()


def prepare_chat_context(
    db: Session,
    user: User | None,
    request: ChatRequest,
    messages: list[dict[str, Any]],
    last_content: Any,
) -> tuple[ChatSession | None, DiagnosisRecord | None, list[dict[str, Any]]]:
    """准备聊天上下文：加载历史、保存诊断记录、更新会话

    未登录时直接返回原消息，不做持久化。
    """
    if not user:
        return None, None, messages

    session, messages = load_session_history(
        db, request.session_id, user.id, messages
    )

    diagnosis = save_diagnosis_record(
        db,
        user=user,
        mode=build_mode_from_system(request.system),
        symptom=last_content if is_text_content(last_content) else "含图片",
        ai_model=request.model,
        project_model=request.project,
        has_image=not is_text_content(last_content),
    )

    if session:
        update_session(db, session, messages)

    return session, diagnosis, messages


async def _safe_stream_generator(
    payload: dict[str, Any]
) -> AsyncGenerator[str, None]:
    """安全流式生成器：将上游异常转换为 SSE error 事件"""
    try:
        async for chunk in stream_chat(payload):
            yield chunk
    except HTTPException as exc:
        yield (
            f"event: error\n"
            f"data: {json.dumps({'detail': exc.detail}, ensure_ascii=False)}\n\n"
        )
    except Exception as exc:  # noqa: BLE001
        yield (
            f"event: error\n"
            f"data: {json.dumps({'detail': f'流式输出异常: {exc}'}, ensure_ascii=False)}\n\n"
        )


async def execute_chat_sync(
    db: Session,
    user: User | None,
    request: ChatRequest,
) -> dict[str, Any]:
    """非流式聊天完整流程"""
    validate_and_prepare_request(request)
    messages, last_content = get_request_messages(request)
    _, diagnosis, messages = prepare_chat_context(
        db, user, request, messages, last_content
    )

    payload = build_chat_payload(request, messages)
    result = await chat_sync(payload)

    if diagnosis:
        update_diagnosis_result(db, diagnosis, result)
    return result


def execute_chat_stream(
    request: ChatRequest,
    user: User | None = None,
    db: Session | None = None,
) -> StreamingResponse:
    """流式聊天完整流程"""
    validate_and_prepare_request(request)
    messages, last_content = get_request_messages(request)

    if db is not None and user is not None:
        prepare_chat_context(db, user, request, messages, last_content)

    payload = build_chat_payload(request, messages)
    return StreamingResponse(
        _safe_stream_generator(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
