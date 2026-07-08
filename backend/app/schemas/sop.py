"""SOP（标准诊断流程）请求/响应 Schema"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MeasurementItem(BaseModel):
    """测量项定义"""

    name: str
    expected_value: str
    unit: str
    tolerance: str | None = None


class BranchOption(BaseModel):
    """决策分支选项（数据库/响应形态）"""

    label: str
    value: str
    next_step_id: int | None = None


class BranchOptionCreate(BaseModel):
    """决策分支选项（创建形态，使用步骤序号而非数据库 ID）"""

    label: str
    value: str
    next_step_number: int | None = None


class SOPStepBase(BaseModel):
    """SOP 步骤基础字段"""

    step_number: int = Field(..., ge=1)
    step_type: Literal["instruction", "check", "decision", "measurement"]
    title: str | None = Field(default=None, max_length=200)
    content: str
    check_items: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    measurements: list[MeasurementItem] = Field(default_factory=list)
    pass_criteria: str | None = None
    fail_criteria: str | None = None
    component_refs: list[str] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)


class SOPStepCreate(SOPStepBase):
    """创建 SOP 步骤（通过 step_number 引用下一步）"""

    next_step_number: int | None = None
    fail_step_number: int | None = None
    branch_options: list[BranchOptionCreate] = Field(default_factory=list)


class SOPStepResponse(SOPStepBase):
    """SOP 步骤响应"""

    id: int
    sop_id: int
    next_step_id: int | None = None
    fail_next_step_id: int | None = None
    branch_options: list[BranchOption] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SOPBase(BaseModel):
    """SOP 模板基础字段"""

    code: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    project_code: str | None = Field(default=None, max_length=50)
    fault_type: str = Field(..., min_length=1, max_length=50)
    keywords: list[str] = Field(default_factory=list)
    source: str = Field(default="", max_length=500)
    version: str = Field(default="1.0", max_length=20)
    is_active: bool = True

    @field_validator("keywords", mode="before")
    @classmethod
    def _normalize_keywords(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v or []


class SOPCreate(SOPBase):
    """创建 SOP 请求"""

    steps: list[SOPStepCreate] = Field(default_factory=list)


class SOPUpdate(BaseModel):
    """更新 SOP 请求（全字段可选）"""

    code: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    project_code: str | None = Field(default=None, max_length=50)
    fault_type: str | None = Field(default=None, min_length=1, max_length=50)
    keywords: list[str] | None = None
    source: str | None = Field(default=None, max_length=500)
    version: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    steps: list[SOPStepCreate] | None = None

    @field_validator("keywords", mode="before")
    @classmethod
    def _normalize_keywords(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v or []


class SOPResponse(SOPBase):
    """SOP 模板详情响应"""

    id: int
    created_at: datetime
    updated_at: datetime
    steps: list[SOPStepResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, value: datetime) -> str:
        return value.isoformat() if value else ""


class SOPListItem(BaseModel):
    """SOP 列表项"""

    id: int
    code: str
    title: str
    project_code: str | None
    fault_type: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SOPSessionStart(BaseModel):
    """启动 SOP 会话请求"""

    project_code: str | None = Field(default=None, max_length=50)
    fault_type: str = Field(..., max_length=50)
    sop_id: int | None = None
    symptom: str | None = Field(default=None, max_length=2000)
    diagnosis_record_id: int | None = None


class SOPSessionAction(BaseModel):
    """推进 SOP 会话请求"""

    action: Literal["continue", "answer", "finish", "abandon"]
    answer: str | None = None
    step_id: int | None = None
    note: str | None = None


class SOPSessionStepState(BaseModel):
    """会话当前/下一步骤的精简信息"""

    id: int
    step_number: int
    step_type: str
    title: str | None
    content: str


class SOPSessionResponse(BaseModel):
    """SOP 会话状态响应"""

    id: int
    status: str
    project_code: str | None
    fault_type: str
    sop_id: int
    current_step: SOPSessionStepState | None = None
    next_step: SOPSessionStepState | None = None
    step_log: list[dict] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("started_at", "finished_at")
    def _serialize_dt(self, value: datetime | None) -> str:
        return value.isoformat() if value else ""
