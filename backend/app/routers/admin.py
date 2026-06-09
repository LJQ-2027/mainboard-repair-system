"""管理后台路由"""

import datetime
from collections import Counter

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diagnosis import DiagnosisRecord
from app.models.knowledge import KnowledgeBaseEntry
from app.models.user import User
from app.services.auth import get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """管理后台首页 - 数据统计看板"""
    # 总诊断次数
    total_diagnoses = db.query(DiagnosisRecord).count()

    # 今日诊断
    today = datetime.datetime.utcnow().date()
    today_count = db.query(DiagnosisRecord).filter(
        DiagnosisRecord.created_at >= today
    ).count()

    # 用户数
    user_count = db.query(User).count()

    # 知识库条目
    kb_count = db.query(KnowledgeBaseEntry).count()

    # 最近 7 天趋势
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    recent = db.query(DiagnosisRecord).filter(
        DiagnosisRecord.created_at >= week_ago
    ).all()
    daily_counts = Counter(r.created_at.date() for r in recent)

    # 故障类型分布
    modes = Counter(r.mode for r in recent)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_diagnoses": total_diagnoses,
        "today_count": today_count,
        "user_count": user_count,
        "kb_count": kb_count,
        "daily_counts": dict(daily_counts),
        "modes": dict(modes),
    })


@router.get("/knowledge", response_class=HTMLResponse)
def admin_knowledge(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """知识库管理"""
    entries = db.query(KnowledgeBaseEntry).order_by(KnowledgeBaseEntry.category, KnowledgeBaseEntry.title).all()
    categories = db.query(KnowledgeBaseEntry.category).distinct().all()
    return templates.TemplateResponse("knowledge.html", {
        "request": request,
        "user": user,
        "entries": entries,
        "categories": [c[0] for c in categories],
    })


@router.post("/knowledge/add")
def add_knowledge(
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    keywords: str = Form(""),
    source: str = Form(""),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """添加知识库条目"""
    entry = KnowledgeBaseEntry(
        category=category,
        title=title,
        content=content,
        keywords=keywords,
        source=source,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)


@router.get("/knowledge/{entry_id}/delete")
def delete_knowledge(entry_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """删除知识库条目"""
    entry = db.query(KnowledgeBaseEntry).get(entry_id)
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)


@router.get("/knowledge/{entry_id}/toggle")
def toggle_knowledge(entry_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """切换知识库条目启用状态"""
    entry = db.query(KnowledgeBaseEntry).get(entry_id)
    if entry:
        entry.is_active = not entry.is_active
        db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)
