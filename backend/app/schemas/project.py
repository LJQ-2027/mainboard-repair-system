"""Project 请求/响应 Schema"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="", max_length=50)

    schematic_url: str = Field(default="", max_length=500)
    schematic_name: str = Field(default="", max_length=200)
    layout_url: str = Field(default="", max_length=500)
    layout_name: str = Field(default="", max_length=200)
    bom_url: str = Field(default="", max_length=500)
    bom_name: str = Field(default="", max_length=200)
    sop_url: str = Field(default="", max_length=500)
    sop_name: str = Field(default="", max_length=200)

    @field_validator("code")
    @classmethod
    def code_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("项目编码只能包含字母、数字、下划线和连字符")
        return v


class ProjectCreate(ProjectBase):
    """创建项目请求"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目请求（全部可选）"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    version: str | None = Field(default=None, max_length=50)
    schematic_url: str | None = Field(default=None, max_length=500)
    schematic_name: str | None = Field(default=None, max_length=200)
    layout_url: str | None = Field(default=None, max_length=500)
    layout_name: str | None = Field(default=None, max_length=200)
    bom_url: str | None = Field(default=None, max_length=500)
    bom_name: str | None = Field(default=None, max_length=200)
    sop_url: str | None = Field(default=None, max_length=500)
    sop_name: str | None = Field(default=None, max_length=200)


class ProjectResponse(ProjectBase):
    """项目响应"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectWithStats(ProjectResponse):
    """项目响应（含诊断统计）"""
    diagnosis_count: int = 0
