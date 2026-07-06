"""诊断记录请求/响应 Schema"""

from pydantic import BaseModel, ConfigDict, Field


class StructuredDiagnosis(BaseModel):
    """AI 结构化诊断结果"""

    fault_type: str | None = Field(default=None, description="故障类型")
    confidence: str | None = Field(default=None, description="置信度，如 high/medium/low 或百分比")
    summary: str | None = Field(default=None, description="一句话摘要")
    recommended_tests: list[str] = Field(default_factory=list, description="建议测试项")
    repair_actions: list[str] = Field(default_factory=list, description="维修动作建议")
    warnings: list[str] = Field(default_factory=list, description="注意事项/风险提示")
    references: list[str] = Field(default_factory=list, description="参考来源")


class DiagnosisRecordResponse(BaseModel):
    """诊断记录响应（含结构化结果）"""

    id: int
    mode: str
    symptom: str | None
    result_text: str | None
    structured_result: StructuredDiagnosis | None
    ai_model: str | None
    has_image: bool
    project_model: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)
