"""SOP（标准诊断流程）数据模型

定义可执行的诊断 SOP 模板、步骤以及用户执行会话。
"""

import json

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base, _now_utc


class DiagnosisSOP(Base):
    """诊断 SOP 模板"""

    __tablename__ = "diagnosis_sops"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    project_code = Column(String(50), index=True, nullable=True)
    fault_type = Column(String(50), index=True, nullable=False)
    keywords = Column(String(500), default="")
    source = Column(String(500), default="")
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now_utc)
    updated_at = Column(DateTime, default=_now_utc, onupdate=_now_utc)


class SOPStep(Base):
    """SOP 步骤"""

    __tablename__ = "diagnosis_sop_steps"

    id = Column(Integer, primary_key=True)
    sop_id = Column(
        Integer,
        ForeignKey("diagnosis_sops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(20), nullable=False)  # instruction / check / decision / measurement
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    check_items = Column(Text, default="[]")  # JSON list[str]
    required_tools = Column(Text, default="[]")  # JSON list[str]
    measurements = Column(Text, default="[]")  # JSON list[dict]
    pass_criteria = Column(Text, nullable=True)
    fail_criteria = Column(Text, nullable=True)
    next_step_id = Column(Integer, nullable=True)
    fail_next_step_id = Column(Integer, nullable=True)
    branch_options = Column(Text, default="[]")  # JSON list[dict]
    component_refs = Column(Text, default="[]")  # JSON list[str]
    rule_refs = Column(Text, default="[]")  # JSON list[str]


class SOPSession(Base):
    """SOP 执行会话"""

    __tablename__ = "diagnosis_sop_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_code = Column(String(50), nullable=True)
    fault_type = Column(String(50), nullable=False)
    sop_id = Column(Integer, ForeignKey("diagnosis_sops.id"), nullable=False)
    diagnosis_record_id = Column(
        Integer, ForeignKey("diagnosis_records.id"), nullable=True, index=True
    )
    status = Column(String(20), default="in_progress")  # in_progress / completed / abandoned
    current_step_id = Column(
        Integer, ForeignKey("diagnosis_sop_steps.id"), nullable=True
    )
    step_log = Column(Text, default="[]")  # JSON list[dict]
    started_at = Column(DateTime, default=_now_utc)
    finished_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_now_utc, onupdate=_now_utc)
