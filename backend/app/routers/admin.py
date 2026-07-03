"""管理后台路由"""

import datetime
import json
import os
import re
import shutil
from collections import Counter
from copy import deepcopy
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diagnosis import DiagnosisRecord
from app.models.knowledge import KnowledgeBaseEntry
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate, ProjectWithStats
from app.services.auth import get_optional_user, get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory="app/templates")


def _project_to_dict(project: Project) -> dict:
    """将 Project 模型转换为前端模板需要的 dict（驼峰命名）"""
    return {
        "name": project.name,
        "version": project.version,
        "schematicUrl": project.schematic_url,
        "schematicName": project.schematic_name,
        "layoutUrl": project.layout_url,
        "layoutName": project.layout_name,
        "bomUrl": project.bom_url,
        "bomName": project.bom_name,
        "sopUrl": project.sop_url,
        "sopName": project.sop_name,
    }


def _get_data_dir() -> str:
    """获取项目根目录的 data/ 路径"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


# ---------------------------------------------------------------------------
# HTML 页面
# ---------------------------------------------------------------------------

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
def delete_knowledge(entry_id: int, user = Depends(require_admin), db: Session = Depends(get_db)):
    """删除知识库条目"""
    entry = db.query(KnowledgeBaseEntry).get(entry_id)
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)


@router.get("/knowledge/{entry_id}/toggle")
def toggle_knowledge(entry_id: int, user = Depends(require_admin), db: Session = Depends(get_db)):
    """切换知识库条目启用状态"""
    entry = db.query(KnowledgeBaseEntry).get(entry_id)
    if entry:
        entry.is_active = not entry.is_active
        db.commit()
    return RedirectResponse("/admin/knowledge", status_code=303)


# ---------------------------------------------------------------------------
# 项目资料管理 - HTML 页面
# ---------------------------------------------------------------------------

@router.get("/projects", response_class=HTMLResponse)
def admin_projects(request: Request, user = Depends(get_optional_user), db: Session = Depends(get_db)):
    """项目资料列表"""
    projects = db.query(Project).order_by(Project.code).all()
    projects_list = []
    for p in projects:
        projects_list.append({
            "code": p.code, "name": p.name,
            "version": p.version,
            "has_schematic": bool(p.schematic_url),
            "has_layout": bool(p.layout_url),
            "has_sop": bool(p.sop_url),
        })
    return templates.TemplateResponse("projects.html", {"request": request, "user": user, "projects": projects_list})


@router.get("/projects/{code}/edit", response_class=HTMLResponse)
def admin_project_edit(code: str, request: Request, user = Depends(get_optional_user), db: Session = Depends(get_db)):
    """项目编辑页"""
    project = db.query(Project).filter(Project.code == code).first()
    if not project:
        return RedirectResponse("/admin/projects", 303)
    return templates.TemplateResponse("project_edit.html", {
        "request": request, "user": user,
        "project": {"code": project.code, **_project_to_dict(project)}
    })


@router.post("/projects/{code}/save")
async def admin_project_save(code: str, request: Request, user = Depends(require_admin), db: Session = Depends(get_db)):
    """保存项目修改"""
    form = await request.form()
    project = db.query(Project).filter(Project.code == code).first()
    if not project:
        return RedirectResponse("/admin/projects", 303)

    field_map = {
        "name": "name", "version": "version",
        "schematicUrl": "schematic_url", "schematicName": "schematic_name",
        "layoutUrl": "layout_url", "layoutName": "layout_name",
        "bomUrl": "bom_url", "bomName": "bom_name",
        "sopUrl": "sop_url", "sopName": "sop_name",
    }
    for form_field, attr in field_map.items():
        if form_field in form:
            setattr(project, attr, form[form_field])
    db.commit()
    return RedirectResponse("/admin/projects", 303)


# 允许上传的文件类型白名单（扩展名 -> 期望 MIME 前缀）
ALLOWED_UPLOAD_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

# 最大文件大小：10MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# 允许的项目资料类型
ALLOWED_FILE_TYPES = {"schematic", "layout", "sop", "bom"}


def _sanitize_filename(filename: str) -> str:
    """净化文件名：移除路径遍历、只保留安全字符、限制长度"""
    # 只取文件名部分，丢弃路径
    filename = Path(filename).name
    # 只允许字母、数字、中文、下划线、连字符、点
    filename = re.sub(r"[^\w一-鿿.\-]", "_", filename)
    # 限制长度，保留扩展名
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:96] + ext
    return filename


def _check_file_magic(content: bytes, ext: str) -> bool:
    """通过文件头魔数校验真实类型"""
    magic_map = {
        ".pdf": content[:4] == b"%PDF",
        ".png": content[:8] == b"\x89PNG\r\n\x1a\n",
        ".jpg": content[:2] == b"\xff\xd8",
        ".jpeg": content[:2] == b"\xff\xd8",
        ".docx": content[:4] == b"PK\x03\x04",
        ".xlsx": content[:4] == b"PK\x03\x04",
    }
    return magic_map.get(ext, True)


def _validate_upload_file(file: UploadFile) -> tuple[bool, str]:
    """校验上传文件，返回 (是否有效, 错误消息)"""
    if not file.filename:
        return False, "未选择文件"

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_TYPES:
        return False, f"不支持的文件类型: {ext}。只允许: {', '.join(ALLOWED_UPLOAD_TYPES.keys())}"

    # 检查文件大小（读取前 MAX_UPLOAD_SIZE+1 字节）
    content = file.file.read(MAX_UPLOAD_SIZE + 1)
    file.file.seek(0)
    if len(content) > MAX_UPLOAD_SIZE:
        return False, f"文件大小超过 {MAX_UPLOAD_SIZE // 1024 // 1024}MB 限制"

    # 校验声明的 MIME 类型（允许 image/* 通配）
    declared_type = file.content_type or ""
    expected_type = ALLOWED_UPLOAD_TYPES[ext]
    expected_main, expected_sub = expected_type.split("/", 1)
    declared_main = declared_type.split("/", 1)[0] if "/" in declared_type else ""
    if declared_main != expected_main:
        # MIME 主类型不一致时，进一步校验文件头
        if not _check_file_magic(content, ext):
            return False, f"文件类型不匹配: 声明为 {declared_type}，但实际不是 {ext}"

    return True, ""


def _get_uploads_dir(project_code: str = ""):
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    if project_code:
        base = os.path.join(base, project_code)
    os.makedirs(base, exist_ok=True)
    return base


@router.post("/projects/{code}/upload")
async def admin_project_upload(
    code: str,
    request: Request,
    file: UploadFile = File(...),
    file_type: str = Form("schematic"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传项目文件（原理图/位号图/SOP/BOM）- 带安全校验"""
    redirect_base = f"/admin/projects/{code}/edit"

    # 校验 file_type 参数
    if file_type not in ALLOWED_FILE_TYPES:
        return RedirectResponse(f"{redirect_base}?error=invalid_file_type", 303)

    # 校验文件
    valid, error_msg = _validate_upload_file(file)
    if not valid:
        return RedirectResponse(f"{redirect_base}?error={error_msg}", 303)

    # 净化文件名
    safe_filename = _sanitize_filename(file.filename)
    ext = Path(safe_filename).suffix

    proj_dir = _get_uploads_dir(code)
    filename = f"{file_type}{ext}"
    dest = os.path.join(proj_dir, filename)

    # 确保目标目录在 uploads 范围内（防目录遍历）
    real_proj_dir = os.path.realpath(proj_dir)
    real_uploads = os.path.realpath(_get_uploads_dir())
    if not real_proj_dir.startswith(real_uploads + os.sep) and real_proj_dir != real_uploads:
        return RedirectResponse(f"{redirect_base}?error=invalid_upload_path", 303)

    # 写入文件（覆盖旧文件）
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 更新数据库中的项目资料链接
    project = db.query(Project).filter(Project.code == code).first()
    if project:
        local_url = f"/uploads/{code}/{filename}"
        if file_type == "schematic":
            project.schematic_url = local_url
            project.schematic_name = safe_filename
        elif file_type == "layout":
            project.layout_url = local_url
            project.layout_name = safe_filename
        elif file_type == "sop":
            project.sop_url = local_url
            project.sop_name = safe_filename
        elif file_type == "bom":
            project.bom_url = local_url
            project.bom_name = safe_filename
        db.commit()

    return RedirectResponse(redirect_base, 303)


@router.post("/projects/add")
async def admin_project_add(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """通过表单添加新项目"""
    form = await request.form()
    code = form.get("code", "").strip()
    name = form.get("name", "").strip()
    version = form.get("version", "").strip()

    if not code or not name:
        return RedirectResponse("/admin/projects?error=code_and_name_required", 303)

    # 校验编码格式
    if not re.match(r"^[a-zA-Z0-9_\-]+$", code):
        return RedirectResponse("/admin/projects?error=invalid_code", 303)

    # 检查重复
    if db.query(Project).filter(Project.code == code).first():
        return RedirectResponse(f"/admin/projects?error=code_exists&code={code}", 303)

    project = Project(code=code, name=name, version=version)
    db.add(project)
    db.commit()
    return RedirectResponse("/admin/projects", 303)


# ---------------------------------------------------------------------------
# 项目资料管理 - REST API
# ---------------------------------------------------------------------------

@router.get("/api/projects", response_model=list[ProjectWithStats])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """列出所有项目及诊断统计"""
    projects = db.query(Project).order_by(Project.code).all()
    result = []
    for p in projects:
        data = ProjectResponse.model_validate(p).model_dump()
        data["diagnosis_count"] = (
            db.query(DiagnosisRecord)
            .filter(DiagnosisRecord.project_model == p.code)
            .count()
        )
        result.append(ProjectWithStats(**data))
    return result


@router.get("/api/projects/{code}", response_model=ProjectResponse)
def get_project(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """获取项目详情"""
    project = db.query(Project).filter(Project.code == code).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.post("/api/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """创建项目"""
    if db.query(Project).filter(Project.code == data.code).first():
        raise HTTPException(status_code=409, detail="项目编码已存在")

    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/api/projects/{code}", response_model=ProjectResponse)
def update_project(
    code: str,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """更新项目"""
    project = db.query(Project).filter(Project.code == code).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/api/projects/{code}", status_code=204)
def delete_project(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """删除项目"""
    project = db.query(Project).filter(Project.code == code).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()
    return None


@router.get("/api/projects/{code}/diagnoses")
def list_project_diagnoses(
    code: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """列出指定项目的诊断记录"""
    project = db.query(Project).filter(Project.code == code).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    records = (
        db.query(DiagnosisRecord)
        .filter(DiagnosisRecord.project_model == code)
        .order_by(DiagnosisRecord.created_at.desc())
        .limit(limit)
        .all()
    )
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


# ---------------------------------------------------------------------------
# 案例库管理
# ---------------------------------------------------------------------------

@router.get("/cases", response_class=HTMLResponse)
def admin_cases(request: Request, user = Depends(get_optional_user)):
    """查看各项目的案例数据"""
    import json5
    cases_file = os.path.join(_get_data_dir(), "project-cases.js")
    if os.path.exists(cases_file):
        with open(cases_file, "r", encoding="utf-8") as f:
            content = f.read()
        idx = content.find("=")
        obj_str = content[idx+1:].strip()
        # 去掉最后的 };（JS 变量声明语法）
        if obj_str.endswith("};"):
            obj_str = obj_str[:-2].rstrip() + "}"
        cases = json5.loads(obj_str)
    else:
        cases = {}

    projects = []
    for code, proj in cases.items():
        rules = proj.get("diagnosisRules", {})
        comps = proj.get("componentMap", {})
        total_components = sum(len(v) for v in comps.values())
        projects.append({
            "code": code,
            "name": proj.get("projectName", code),
            "fault_types": list(rules.keys()),
            "total_rules": sum(len(v) for v in rules.values()),
            "total_components": total_components,
        })

    return templates.TemplateResponse("cases.html", {
        "request": request, "user": user, "projects": projects
    })
