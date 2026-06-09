"""AI 聊天路由"""

from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.ai_proxy import chat_sync, stream_chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(request: Request):
    """AI 对话接口 - 支持流式和非流式"""
    body: Dict[str, Any] = await request.json()
    stream = body.get("stream", True)

    if stream:
        return StreamingResponse(
            stream_chat(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    else:
        return await chat_sync(body)
