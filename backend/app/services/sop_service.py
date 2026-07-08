"""SOP（标准诊断流程）业务服务

提供 SOP 模板的 CRUD、执行会话推进、以及与 AI Chat 的上下文注入。
"""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database import _now_utc
from app.models.sop import DiagnosisSOP, SOPSession, SOPStep
from app.schemas.chat import ChatRequest
from app.schemas.sop import (
    SOPCreate,
    SOPResponse,
    SOPSessionAction,
    SOPSessionResponse,
    SOPSessionStart,
    SOPSessionStepState,
    SOPStepCreate,
    SOPStepResponse,
    SOPUpdate,
)


# ---------------------------------------------------------------------------
# JSON 工具
# ---------------------------------------------------------------------------


def _load_json(text: str | None, default: list | dict | None = None):
    """安全加载 JSON 文本"""
    if default is None:
        default = []
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _dump_json(data: list | dict) -> str:
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Schema 转换
# ---------------------------------------------------------------------------


def _step_response(step: SOPStep) -> SOPStepResponse:
    return SOPStepResponse(
        id=step.id,
        sop_id=step.sop_id,
        step_number=step.step_number,
        step_type=step.step_type,
        title=step.title,
        content=step.content,
        check_items=_load_json(step.check_items),
        required_tools=_load_json(step.required_tools),
        measurements=_load_json(step.measurements),
        pass_criteria=step.pass_criteria,
        fail_criteria=step.fail_criteria,
        next_step_id=step.next_step_id,
        fail_next_step_id=step.fail_next_step_id,
        branch_options=_load_json(step.branch_options),
        component_refs=_load_json(step.component_refs),
        rule_refs=_load_json(step.rule_refs),
    )


def _sop_response(sop: DiagnosisSOP, include_steps: bool = True) -> SOPResponse:
    data = {
        "id": sop.id,
        "code": sop.code,
        "title": sop.title,
        "project_code": sop.project_code,
        "fault_type": sop.fault_type,
        "keywords": [k.strip() for k in (sop.keywords or "").split(",") if k.strip()],
        "source": sop.source or "",
        "version": sop.version or "1.0",
        "is_active": sop.is_active,
        "created_at": sop.created_at,
        "updated_at": sop.updated_at,
    }
    if include_steps:
        steps = sorted(sop.steps, key=lambda s: s.step_number) if sop.steps else []
        data["steps"] = [_step_response(s) for s in steps]
    else:
        data["steps"] = []
    return SOPResponse(**data)


def _step_state(step: SOPStep | None) -> SOPSessionStepState | None:
    if step is None:
        return None
    return SOPSessionStepState(
        id=step.id,
        step_number=step.step_number,
        step_type=step.step_type,
        title=step.title,
        content=step.content,
    )


def _session_response(session: SOPSession, db: Session) -> SOPSessionResponse:
    current_step = None
    if session.current_step_id:
        current_step = db.query(SOPStep).get(session.current_step_id)

    next_step = None
    if current_step:
        next_id = _resolve_next_step_id(db, session, current_step, "continue", None)
        if next_id:
            next_step = db.query(SOPStep).get(next_id)

    return SOPSessionResponse(
        id=session.id,
        status=session.status,
        project_code=session.project_code,
        fault_type=session.fault_type,
        sop_id=session.sop_id,
        current_step=_step_state(current_step),
        next_step=_step_state(next_step),
        step_log=_load_json(session.step_log),
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


# ---------------------------------------------------------------------------
# CRUD：SOP 模板
# ---------------------------------------------------------------------------


def _create_steps(
    db: Session,
    sop_id: int,
    steps_data: list[SOPStepCreate],
) -> None:
    """批量创建步骤，并通过 step_number 解析分支目标"""
    step_models = []
    for item in steps_data:
        step = SOPStep(
            sop_id=sop_id,
            step_number=item.step_number,
            step_type=item.step_type,
            title=item.title,
            content=item.content,
            check_items=_dump_json(item.check_items),
            required_tools=_dump_json(item.required_tools),
            measurements=_dump_json([m.model_dump() for m in item.measurements]),
            pass_criteria=item.pass_criteria,
            fail_criteria=item.fail_criteria,
            branch_options=_dump_json(
                [
                    {"label": b.label, "value": b.value, "next_step_id": None}
                    for b in item.branch_options
                ]
            ),
            component_refs=_dump_json(item.component_refs),
            rule_refs=_dump_json(item.rule_refs),
        )
        db.add(step)
        step_models.append(step)
    db.flush()  # 获取自增 ID

    # 建立 step_number -> id 映射，回填分支引用
    number_to_id = {s.step_number: s.id for s in step_models}
    for item, step in zip(steps_data, step_models):
        step.next_step_id = number_to_id.get(item.next_step_number) if item.next_step_number else None
        step.fail_next_step_id = number_to_id.get(item.fail_step_number) if item.fail_step_number else None
        if item.branch_options:
            branch_options = []
            for b in item.branch_options:
                branch_options.append(
                    {
                        "label": b.label,
                        "value": b.value,
                        "next_step_id": number_to_id.get(b.next_step_number)
                        if b.next_step_number
                        else None,
                    }
                )
            step.branch_options = _dump_json(branch_options)


def create_sop(db: Session, data: SOPCreate) -> SOPResponse:
    """创建 SOP 模板（含步骤）"""
    if db.query(DiagnosisSOP).filter(DiagnosisSOP.code == data.code).first():
        raise HTTPException(status_code=409, detail="SOP 编码已存在")

    sop = DiagnosisSOP(
        code=data.code,
        title=data.title,
        project_code=data.project_code,
        fault_type=data.fault_type,
        keywords=",".join(data.keywords),
        source=data.source,
        version=data.version,
        is_active=data.is_active,
    )
    db.add(sop)
    db.flush()

    if data.steps:
        _create_steps(db, sop.id, data.steps)

    db.commit()
    db.refresh(sop)
    return _sop_response(sop)


def update_sop(db: Session, sop_id: int, data: SOPUpdate) -> SOPResponse:
    """更新 SOP 模板（如提供 steps 则整量替换）"""
    sop = db.query(DiagnosisSOP).get(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    update = data.model_dump(exclude_unset=True)
    if "steps" in update:
        update.pop("steps")

    if "code" in update and update["code"] != sop.code:
        if db.query(DiagnosisSOP).filter(DiagnosisSOP.code == update["code"]).first():
            raise HTTPException(status_code=409, detail="SOP 编码已存在")

    if "keywords" in update:
        update["keywords"] = ",".join(update["keywords"])

    for field, value in update.items():
        setattr(sop, field, value)

    if data.steps is not None:
        # 整量替换步骤
        db.query(SOPStep).filter(SOPStep.sop_id == sop.id).delete()
        if data.steps:
            _create_steps(db, sop.id, data.steps)

    db.commit()
    db.refresh(sop)
    return _sop_response(sop)


def delete_sop(db: Session, sop_id: int) -> None:
    sop = db.query(DiagnosisSOP).get(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")
    db.delete(sop)
    db.commit()


def get_sop(db: Session, sop_id: int) -> SOPResponse:
    sop = db.query(DiagnosisSOP).get(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")
    return _sop_response(sop)


def list_sops(
    db: Session,
    project_code: str | None = None,
    fault_type: str | None = None,
    q: str | None = None,
    limit: int = 100,
    active_only: bool = True,
) -> list[SOPResponse]:
    query = db.query(DiagnosisSOP)
    if active_only:
        query = query.filter(DiagnosisSOP.is_active.is_(True))
    if project_code:
        query = query.filter(
            (DiagnosisSOP.project_code == project_code) | (DiagnosisSOP.project_code.is_(None))
        )
    if fault_type:
        query = query.filter(DiagnosisSOP.fault_type == fault_type)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (DiagnosisSOP.title.like(like))
            | (DiagnosisSOP.code.like(like))
            | (DiagnosisSOP.fault_type.like(like))
            | (DiagnosisSOP.keywords.like(like))
        )
    sops = query.order_by(DiagnosisSOP.fault_type, DiagnosisSOP.code).limit(limit).all()
    return [_sop_response(s, include_steps=False) for s in sops]


# ---------------------------------------------------------------------------
# 匹配与执行
# ---------------------------------------------------------------------------


def match_sop(
    db: Session,
    project_code: str | None,
    fault_type: str,
) -> DiagnosisSOP | None:
    """按项目和故障类型匹配最合适的活跃 SOP"""
    # 1. 项目专属 + 故障类型
    if project_code:
        sop = (
            db.query(DiagnosisSOP)
            .filter(
                DiagnosisSOP.project_code == project_code,
                DiagnosisSOP.fault_type == fault_type,
                DiagnosisSOP.is_active.is_(True),
            )
            .first()
        )
        if sop:
            return sop

    # 2. 全局 + 故障类型
    sop = (
        db.query(DiagnosisSOP)
        .filter(
            DiagnosisSOP.project_code.is_(None),
            DiagnosisSOP.fault_type == fault_type,
            DiagnosisSOP.is_active.is_(True),
        )
        .first()
    )
    if sop:
        return sop

    return None


def _first_step(db: Session, sop_id: int) -> SOPStep:
    return (
        db.query(SOPStep)
        .filter(SOPStep.sop_id == sop_id)
        .order_by(SOPStep.step_number)
        .first()
    )


def start_session(
    db: Session,
    user_id: int | None,
    data: SOPSessionStart,
) -> SOPSessionResponse:
    """启动一个新的 SOP 执行会话"""
    if data.sop_id:
        sop = db.query(DiagnosisSOP).get(data.sop_id)
        if not sop or not sop.is_active:
            raise HTTPException(status_code=404, detail="SOP 不存在或未启用")
    else:
        sop = match_sop(db, data.project_code, data.fault_type)
        if not sop:
            raise HTTPException(
                status_code=404,
                detail="未找到匹配的 SOP，请指定 sop_id 或检查 project_code/fault_type",
            )

    first = _first_step(db, sop.id)
    if not first:
        raise HTTPException(status_code=400, detail="该 SOP 尚未配置步骤")

    session = SOPSession(
        user_id=user_id,
        project_code=data.project_code or sop.project_code,
        fault_type=data.fault_type,
        sop_id=sop.id,
        diagnosis_record_id=data.diagnosis_record_id,
        status="in_progress",
        current_step_id=first.id,
        step_log=_dump_json([]),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_response(session, db)


def get_session(db: Session, session_id: int, user_id: int | None) -> SOPSession:
    """获取会话并校验归属"""
    session = db.query(SOPSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="SOP 会话不存在")
    if user_id is not None and session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该 SOP 会话")
    return session


def _resolve_next_step_id(
    db: Session,
    session: SOPSession,
    current: SOPStep,
    action: str,
    answer: str | None,
) -> int | None:
    """根据当前步骤、动作和答案，解析下一步 ID"""
    if action in ("finish", "abandon"):
        return None

    # 决策分支：匹配 answer
    if answer and current.branch_options:
        options = _load_json(current.branch_options)
        for opt in options:
            if opt.get("value") == answer:
                target = opt.get("next_step_id")
                if target:
                    return target
                break

    # 显式失败分支
    if answer == "fail" and current.fail_next_step_id:
        return current.fail_next_step_id

    # 默认成功分支
    if current.next_step_id:
        return current.next_step_id

    # 按 step_number 顺序推断下一步
    nxt = (
        db.query(SOPStep)
        .filter(SOPStep.sop_id == current.sop_id, SOPStep.step_number > current.step_number)
        .order_by(SOPStep.step_number)
        .first()
    )
    return nxt.id if nxt else None


def continue_session(
    db: Session,
    session_id: int,
    user_id: int | None,
    action: SOPSessionAction,
) -> SOPSessionResponse:
    """推进 SOP 会话"""
    session = get_session(db, session_id, user_id)
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="会话已结束")

    current = db.query(SOPStep).get(session.current_step_id) if session.current_step_id else None
    if current is None and action not in ("finish", "abandon"):
        raise HTTPException(status_code=400, detail="当前没有可执行的步骤")

    log = _load_json(session.step_log)
    now = datetime.now(timezone.utc).isoformat()

    if action.action in ("finish", "abandon"):
        log.append(
            {
                "step_id": current.id if current else None,
                "action": action.action,
                "answer": action.answer,
                "note": action.note,
                "timestamp": now,
            }
        )
        session.step_log = _dump_json(log)
        session.status = "completed" if action.action == "finish" else "abandoned"
        session.finished_at = _now_utc()
        session.current_step_id = None
        db.commit()
        return _session_response(session, db)

    # continue / answer
    log.append(
        {
            "step_id": current.id,
            "step_number": current.step_number,
            "action": action.action,
            "answer": action.answer,
            "note": action.note,
            "timestamp": now,
        }
    )

    next_id = _resolve_next_step_id(db, session, current, action.action, action.answer)
    session.current_step_id = next_id
    if next_id is None:
        session.status = "completed"
        session.finished_at = _now_utc()
    session.step_log = _dump_json(log)
    db.commit()
    return _session_response(session, db)


# ---------------------------------------------------------------------------
# Chat 上下文注入
# ---------------------------------------------------------------------------


def _find_matching_sop(
    db: Session,
    project_code: str | None,
    symptom: str,
) -> DiagnosisSOP | None:
    """根据项目和症状文本匹配 SOP"""
    symptom_lower = (symptom or "").lower()
    if not symptom_lower:
        return None

    query = db.query(DiagnosisSOP).filter(DiagnosisSOP.is_active.is_(True))
    if project_code:
        query = query.filter(
            (DiagnosisSOP.project_code == project_code) | (DiagnosisSOP.project_code.is_(None))
        )
    sops = query.all()

    # 优先精确匹配 fault_type
    for sop in sops:
        if sop.fault_type and sop.fault_type.lower() in symptom_lower:
            return sop

    # 其次匹配关键词
    for sop in sops:
        keywords = [k.strip().lower() for k in (sop.keywords or "").split(",") if k.strip()]
        if any(k in symptom_lower for k in keywords):
            return sop

    return None


def build_sop_context(
    db: Session,
    project_code: str | None,
    symptom: str,
    sop_session_id: int | None = None,
    max_steps: int = 8,
) -> str | None:
    """为 AI Chat 构建 SOP 上下文文本；未匹配时返回 None"""
    sop = None
    session = None

    if sop_session_id:
        session = db.query(SOPSession).get(sop_session_id)
        if session:
            sop = db.query(DiagnosisSOP).get(session.sop_id)
            project_code = project_code or session.project_code

    if sop is None:
        sop = _find_matching_sop(db, project_code, symptom)

    if sop is None:
        return None

    steps = (
        db.query(SOPStep)
        .filter(SOPStep.sop_id == sop.id)
        .order_by(SOPStep.step_number)
        .limit(max_steps)
        .all()
    )

    lines = [
        "【SOP诊断上下文】",
        f"适用故障类型：{sop.fault_type}",
        f"SOP标题：{sop.title}",
        f"适用项目：{sop.project_code or '通用'}",
        f"版本：{sop.version}",
    ]

    if steps:
        lines.append("标准诊断步骤（供参考，请结合实际情况判断）：")
        for step in steps:
            title = f" - {step.title}" if step.title else ""
            lines.append(f"{step.step_number}. {step.step_type}{title}：{step.content}")
            if step.required_tools:
                tools = _load_json(step.required_tools)
                if tools:
                    lines.append(f"   所需工具：{', '.join(str(t) for t in tools)}")
            if step.measurements:
                measurements = _load_json(step.measurements)
                for m in measurements:
                    lines.append(
                        f"   测量项 {m.get('name')}：标准值 {m.get('expected_value')} {m.get('unit')}"
                    )

    if session and session.current_step_id:
        current = db.query(SOPStep).get(session.current_step_id)
        if current:
            lines.append(f"\n当前执行中步骤：步骤{current.step_number} {current.title or ''}")
            lines.append(current.content)

    return "\n".join(lines)


def enrich_system_prompt(
    db: Session,
    request: ChatRequest,
    symptom: str,
) -> None:
    """直接修改 request.system，注入 SOP 上下文（避免重复注入）"""
    if "【SOP诊断上下文】" in (request.system or ""):
        return
    context = build_sop_context(db, request.project or None, symptom, request.sop_session_id)
    if context:
        request.system = (request.system or "") + "\n\n" + context
