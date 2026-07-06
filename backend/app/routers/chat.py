"""AI 聊天路由 - 支持多轮对话和诊断记录

业务逻辑已下沉到 app.services.chat_service，路由层仅负责：
- HTTP 参数解析与依赖注入
- 调用 chat_service 完成实际处理
- 返回响应
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diagnosis import DiagnosisRecord
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRecordResponse, StructuredDiagnosis
from app.services.auth import get_current_active_user, get_optional_user
from app.services.chat_service import execute_chat_stream, execute_chat_sync

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """AI 对话接口 - 免登录可用，登录后保存记录"""
    if request.stream:
        return execute_chat_stream(request, current_user, db)
    return await execute_chat_sync(db, current_user, request)


@router.post("/chat/sessions")
def create_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """创建新会话"""
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title}


@router.get("/chat/sessions")
def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的会话"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).limit(50).all()
    return [
        {"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()}
        for s in sessions
    ]


@router.get("/history")
def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """查询当前用户的诊断历史"""
    records = db.query(DiagnosisRecord).filter(
        DiagnosisRecord.user_id == current_user.id
    ).order_by(DiagnosisRecord.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "mode": r.mode,
            "symptom": r.symptom,
            "result_text": r.result_text[:200] if r.result_text else "",
            "ai_model": r.ai_model,
            "has_image": r.has_image,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/history/{record_id}", response_model=DiagnosisRecordResponse)
def get_history_detail(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取单条诊断记录详情（含结构化结果）"""
    record = db.query(DiagnosisRecord).filter(
        DiagnosisRecord.id == record_id,
        DiagnosisRecord.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="诊断记录不存在")

    structured = None
    if record.structured_result:
        try:
            structured = StructuredDiagnosis(**json.loads(record.structured_result))
        except (json.JSONDecodeError, TypeError):
            structured = None

    return DiagnosisRecordResponse(
        id=record.id,
        mode=record.mode,
        symptom=record.symptom,
        result_text=record.result_text,
        structured_result=structured,
        ai_model=record.ai_model,
        has_image=record.has_image,
        project_model=record.project_model,
        created_at=record.created_at.isoformat(),
    )
