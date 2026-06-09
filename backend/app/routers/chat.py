"""AI 聊天路由 - 支持多轮对话和诊断记录"""

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diagnosis import DiagnosisRecord
from app.models.session import ChatSession
from app.models.user import User
from app.services.ai_proxy import chat_sync, stream_chat
from app.services.auth import get_current_active_user, get_optional_user
from app.utils.validators import sanitize_input, validate_symptom, validate_system_prompt

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """AI 对话接口 - 免登录可用，登录后保存记录"""
    body: Dict[str, Any] = await request.json()
    stream = body.get("stream", True)

    # ---- 输入校验 ----
    system_prompt = body.get("system", "")
    if system_prompt:
        ok, err = validate_system_prompt(system_prompt)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        if "引用" not in system_prompt and "维修" in system_prompt:
            body["system"] = system_prompt + "\n\n## 重要：请在你的回复中标注引用来源\n- 如果参考了知识库信息，用 [知识库: 标题] 标注\n- 如果参考了本地案例，用 [案例: 故障类型] 标注\n- 如果是基于专业经验，用 [经验] 标注"

    user_msg = body.get("messages", [{}])[-1].get("content", "")
    if isinstance(user_msg, str) and user_msg:
        ok, err = validate_symptom(user_msg)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        user_msg = sanitize_input(user_msg)
        if isinstance(body["messages"][-1]["content"], str):
            body["messages"][-1]["content"] = user_msg

    # ---- 会话 + 记录（仅登录时保存）----
    session_id = body.pop("session_id", None)
    diagnosis = None

    if current_user:
        # 加载会话历史
        if session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            ).first()
            if session:
                history_msgs = json.loads(session.messages_json)
                body["messages"] = history_msgs[-10:] + body.get("messages", [])

        # 保存诊断记录
        diagnosis = DiagnosisRecord(
            user_id=current_user.id,
            mode=body.get("system", "").find("AI 智能诊断") >= 0 and "AI" or "对话",
            symptom=body.get("messages", [{}])[-1].get("content", "") if isinstance(body.get("messages", [{}])[-1].get("content"), str) else "含图片",
            ai_model=body.get("model", ""),
            project_model=body.get("project", ""),
            has_image=not isinstance(body.get("messages", [{}])[-1].get("content", ""), str),
            result_text="",
        )
        db.add(diagnosis)
        db.commit()

        # 更新会话
        if session_id:
            session.messages_json = json.dumps(body.get("messages", []), ensure_ascii=False)
            if len(body.get("messages", [])) == 1:
                first_msg = body.get("messages", [{}])[0]
                content = first_msg.get("content", "") if isinstance(first_msg.get("content"), str) else "图片分析"
                session.title = content[:50]
            db.commit()

    if stream:
        return StreamingResponse(
            stream_chat(body),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    else:
        result = await chat_sync(body)
        if diagnosis:
            text = ""
            if isinstance(result, dict) and "content" in result:
                for block in result.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")
            diagnosis.result_text = text
            db.commit()
        return result


@router.post("/chat/sessions")
def create_session(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title}


@router.get("/chat/sessions")
def list_sessions(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).limit(50).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]


@router.get("/history")
def get_history(limit: int = 50, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    records = db.query(DiagnosisRecord).filter(
        DiagnosisRecord.user_id == current_user.id
    ).order_by(DiagnosisRecord.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "mode": r.mode, "symptom": r.symptom, "result_text": r.result_text[:200],
             "ai_model": r.ai_model, "has_image": r.has_image, "created_at": r.created_at.isoformat()} for r in records]
