"""管理后台路由"""

import datetime
import json
import os
import re
from collections import Counter
from copy import deepcopy

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diagnosis import DiagnosisRecord
from app.models.knowledge import KnowledgeBaseEntry
from app.models.user import User
from app.services.auth import get_optional_user, get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, user = Depends(get_optional_user), db: Session = Depends(get_db)):
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
def admin_knowledge(request: Request, user = Depends(get_optional_user), db: Session = Depends(get_db)):
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
def delete_knowledge(entry_id: int, user = Depends(get_optional_user), db: Session = Depends(get_db)):
    """删除知识库条目"""
    entry = db.query(KnowledgeBaseEntry).get(entry_id)
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)


# ====== 项目资料管理 ======

def _get_data_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")

def _read_project_db():
    """读取 project-database.js 返回 Python dict"""
    filepath = os.path.join(_get_data_dir(), "project-database.js")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find("=")
    obj_str = content[idx+1:].strip().rstrip(";")
    import json5
    return json5.loads(obj_str)

def _write_project_db(data: dict):
    """写回 project-database.js"""
    filepath = os.path.join(_get_data_dir(), "project-database.js")
    js = "const projectDatabase = " + json.dumps(data, ensure_ascii=False, indent=4) + ";"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("// 项目资料库\n// 从管理后台维护，刷新前端页面即可生效\n" + js)


@router.get("/projects", response_class=HTMLResponse)
def admin_projects(request: Request, user = Depends(get_optional_user)):
    db = _read_project_db()
    projects = []
    for code, p in db.items():
        projects.append({
            "code": code, "name": p.get("name",""),
            "version": p.get("version",""),
            "has_schematic": bool(p.get("schematicUrl")),
            "has_layout": bool(p.get("layoutUrl")),
            "has_sop": bool(p.get("sopUrl")),
        })
    return templates.TemplateResponse("projects.html", {"request": request, "user": user, "projects": projects})


@router.get("/projects/{code}/edit", response_class=HTMLResponse)
def admin_project_edit(code: str, request: Request, user = Depends(get_optional_user)):
    db = _read_project_db()
    if code not in db:
        return RedirectResponse("/admin/projects", 303)
    return templates.TemplateResponse("project_edit.html", {
        "request": request, "user": user, "project": {"code": code, **db[code]}
    })


@router.post("/projects/{code}/save")
async def admin_project_save(code: str, request: Request, user = Depends(get_optional_user)):
    """保存项目修改"""
    form = await request.form()
    db = _read_project_db()
    if code not in db:
        return RedirectResponse("/admin/projects", 303)
    for field in ["name","version","schematicUrl","schematicName","layoutUrl","layoutName",
                   "bomUrl","bomName","sopUrl","sopName"]:
        if field in form:
            db[code][field] = form[field]
    _write_project_db(db)
    return RedirectResponse("/admin/projects", 303)


@router.post("/projects/add")
async def admin_project_add(request: Request, user = Depends(get_optional_user)):
    form = await request.form()
    code = form.get("code", "").strip()
    if not code:
        return RedirectResponse("/admin/projects", 303)
    db = _read_project_db()
    db[code] = {
        "name": form.get("name",""),
        "version": form.get("version",""),
        "schematicUrl": form.get("schematicUrl",""),
        "schematicName": "",
        "layoutUrl": form.get("layoutUrl",""),
        "layoutName": "",
        "bomUrl": "",
        "bomName": "",
        "sopUrl": form.get("sopUrl",""),
        "sopName": "",
    }
    _write_project_db(db)
    return RedirectResponse("/admin/projects", 303)


@router.get("/knowledge/{entry_id}/toggle")
def toggle_knowledge(entry_id: int, user = Depends(get_optional_user), db: Session = Depends(get_db)):
    """切换知识库条目启用状态"""
    entry = db.query(KnowledgeBaseEntry).get(entry_id)
    if entry:
        entry.is_active = not entry.is_active
        db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)
