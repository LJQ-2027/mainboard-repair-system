"""AI 代理服务 - 支持 Kimi / Anthropic / DeepSeek 多平台"""

import json
from typing import Any, AsyncGenerator, Dict, Literal, Tuple

import httpx
from fastapi import HTTPException

from app.config import get_settings

# ========== 提供商配置 ==========
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "kimi": {
        "name": "Kimi (Moonshot)",
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "key_prefix": "sk-",
        "models": [
            "moonshot-v1-vision-preview",
            "moonshot-v1-128k",
            "moonshot-v1-32k",
            "moonshot-v1-8k",
        ],
        "default_model": "moonshot-v1-vision-preview",
        "supports_vision": True,
        "api_format": "openai",
    },
    "kimi-code": {
        "name": "Kimi Code (订阅版)",
        "url": "https://api.kimi.com/coding/v1/messages",
        "key_prefix": "sk-kimi-",
        "models": ["kimi-for-coding", "kimi-k2-thinking", "kimi-k2-thinking-turbo"],
        "default_model": "kimi-for-coding",
        "supports_vision": True,
        "api_format": "anthropic",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "url": "https://api.anthropic.com/v1/messages",
        "key_prefix": "sk-ant-api03-",
        "models": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
        "default_model": "claude-sonnet-4-6",
        "supports_vision": True,
        "api_format": "anthropic",
    },
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/chat/completions",
        "key_prefix": "sk-",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "supports_vision": False,
        "api_format": "openai",
    },
}


def detect_provider(api_key: str) -> Tuple[str, Dict[str, Any]]:
    """检测 API 提供商"""
    settings = get_settings()
    manual = settings.ai_provider
    if manual in PROVIDERS:
        return manual, PROVIDERS[manual]

    for pid, config in PROVIDERS.items():
        if api_key.startswith(config["key_prefix"]):
            return pid, config

    return "deepseek", PROVIDERS["deepseek"]


def _convert_anthropic_content_to_openai(
    content: Any, provider_id: str
) -> Any:
    """将 Anthropic 格式内容转为 OpenAI 兼容格式"""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        config = PROVIDERS.get(provider_id, {})
        supports_vision = config.get("supports_vision", False)

        if not supports_vision:
            parts = []
            has_image = False
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif block.get("type") == "image":
                        has_image = True
            text = "\n".join(parts)
            if has_image:
                text += "\n\n[注意：当前 API 不支持图片分析。建议切换平台以启用原理图视觉分析功能。]"
            return text
        else:
            openai_blocks = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        openai_blocks.append(
                            {"type": "text", "text": block.get("text", "")}
                        )
                    elif block.get("type") == "image":
                        source = block.get("source", {})
                        media_type = source.get("media_type", "image/png")
                        base64_data = source.get("data", "")
                        data_url = f"data:{media_type};base64,{base64_data}"
                        openai_blocks.append(
                            {"type": "image_url", "image_url": {"url": data_url}}
                        )
            return openai_blocks

    return str(content)


def _build_openai_payload(payload: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
    """将 Anthropic 格式请求转为 OpenAI 兼容格式"""
    messages = []
    system = payload.get("system", "")
    if system:
        messages.append({"role": "system", "content": system})

    for msg in payload.get("messages", []):
        content = msg.get("content", "")
        role = msg.get("role", "user")
        converted = _convert_anthropic_content_to_openai(content, provider_id)
        messages.append({"role": role, "content": converted})

    config = PROVIDERS.get(provider_id, PROVIDERS["deepseek"])
    return {
        "model": payload.get("model", config["default_model"]),
        "messages": messages,
        "max_tokens": payload.get("max_tokens", 4096),
        "temperature": payload.get("temperature", 0.7),
        "stream": payload.get("stream", True),
    }


def _convert_openai_sse_to_anthropic(chunk: str) -> str | None:
    """将 OpenAI SSE chunk 转为 Anthropic 格式"""
    try:
        data = json.loads(chunk)
    except json.JSONDecodeError:
        return None

    choices = data.get("choices", [])
    if not choices:
        return None

    choice = choices[0]
    delta = choice.get("delta", {})
    content = delta.get("content", "")

    if choice.get("finish_reason"):
        return json.dumps({"type": "message_stop"}, ensure_ascii=False)

    if content:
        return json.dumps(
            {
                "type": "content_block_delta",
                "index": choice.get("index", 0),
                "delta": {"type": "text_delta", "text": content},
            },
            ensure_ascii=False,
        )

    return None


async def stream_chat(
    payload: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """流式聊天 API 调用"""
    settings = get_settings()
    api_key = settings.anthropic_api_key

    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 ANTHROPIC_API_KEY")

    provider_id, config = detect_provider(api_key)
    api_format = config.get("api_format", "openai")

    # 构建请求
    if api_format == "openai":
        api_payload = _build_openai_payload(payload, provider_id)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    else:
        api_payload = {
            "model": payload.get("model", config["default_model"]),
            "max_tokens": payload.get("max_tokens", 4096),
            "messages": payload.get("messages", []),
            "temperature": payload.get("temperature", 0.7),
            "stream": payload.get("stream", True),
        }
        system = payload.get("system", "")
        if system:
            api_payload["system"] = system
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    stream = payload.get("stream", True)

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            async with client.stream(
                "POST",
                config["url"],
                json=api_payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"API 返回错误: {err_body.decode()[:300]}",
                    )

                if api_format == "openai" and stream:
                    # OpenAI 流式 → 转 Anthropic SSE
                    async for line in response.aiter_lines():
                        line_str = line.strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                yield f'data: {{"type":"message_stop"}}\n\n'
                                continue
                            converted = _convert_openai_sse_to_anthropic(data_str)
                            if converted:
                                yield f"data: {converted}\n\n"
                elif stream:
                    # Anthropic 流式 → 直接转发
                    buffer = b""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            yield (line + b"\n").decode("utf-8", errors="replace")
                    if buffer:
                        yield buffer.decode("utf-8", errors="replace")
                else:
                    # 非流式
                    body = await response.aread()
                    yield body.decode("utf-8")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API 请求超时")
        except httpx.ConnectError as e:
            raise HTTPException(status_code=502, detail=f"无法连接到 API: {e}")


async def chat_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """非流式聊天 API 调用"""
    settings = get_settings()
    api_key = settings.anthropic_api_key

    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 ANTHROPIC_API_KEY")

    provider_id, config = detect_provider(api_key)
    api_format = config.get("api_format", "openai")

    if api_format == "openai":
        api_payload = _build_openai_payload(payload, provider_id)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    else:
        api_payload = {
            "model": payload.get("model", config["default_model"]),
            "max_tokens": payload.get("max_tokens", 4096),
            "messages": payload.get("messages", []),
            "temperature": payload.get("temperature", 0.7),
            "stream": False,
        }
        system = payload.get("system", "")
        if system:
            api_payload["system"] = system
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                config["url"], json=api_payload, headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API 请求超时")
        except httpx.ConnectError as e:
            raise HTTPException(status_code=502, detail=f"无法连接到 API: {e}")


def get_health_info() -> Dict[str, Any]:
    """获取健康检查信息"""
    settings = get_settings()
    api_key = settings.anthropic_api_key
    provider_id, config = detect_provider(api_key) if api_key else ("unknown", None)

    return {
        "status": "ok",
        "api_configured": bool(api_key),
        "provider": config["name"] if config else "未检测",
        "provider_id": provider_id if config else "unknown",
        "default_model": config["default_model"] if config else "N/A",
        "supports_vision": config["supports_vision"] if config else False,
        "models": config["models"] if config else [],
    }
