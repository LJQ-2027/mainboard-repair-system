"""聊天请求/响应 Schema"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: str = "user"
    content: str | list[dict[str, Any]] = ""


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    system: str = ""
    model: str = ""
    max_tokens: int = Field(default=4096, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = True
    session_id: int | None = None
    project: str = ""
    sop_session_id: int | None = Field(
        default=None, description="关联的 SOP 会话 ID，用于注入当前步骤上下文"
    )
    structured: bool = Field(default=False, description="是否返回结构化诊断结果（非流式）")

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v:
            raise ValueError("messages 不能为空")
        return v
