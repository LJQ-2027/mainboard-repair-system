"""AI 代理服务 - 支持 Kimi / Anthropic / DeepSeek 多平台"""

import json
from typing import Any, AsyncGenerator, Dict, Tuple

import httpx
from fastapi import HTTPException

from app.config import get_settings

# ========== 提供商配置 ==========
# 注意：顺序很重要！特定前缀必须排在通用 sk- 前面
PROVIDERS: Dict[str, Dict[str, Any]] = {
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

# 注意：sk- 前缀同时匹配 kimi 和 deepseek
# 如果无法自动区分，请在 .env 中设置 AI_PROVIDER


def detect_provider(api_key: str) -> Tuple[str, Dict[str, Any]]:
    """检测 API 提供商，无法识别时抛出异常"""
    settings = get_settings()
    manual = settings.ai_provider
    if manual in PROVIDERS:
        return manual, PROVIDERS[manual]

    for pid, config in PROVIDERS.items():
        if api_key.startswith(config["key_prefix"]):
            return pid, config

    raise HTTPException(
        status_code=400,
        detail=(
            "无法识别 API Key 对应的提供商，请在 .env 中设置 AI_PROVIDER 为以下之一: "
            f"{list(PROVIDERS.keys())}"
        ),
    )


def _validate_and_detect_provider() -> Tuple[str, str, Dict[str, Any]]:
    """校验 API Key 并检测 provider，返回 (api_key, provider_id, config)"""
    settings = get_settings()
    api_key = settings.anthropic_api_key

    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 ANTHROPIC_API_KEY")

    provider_id, config = detect_provider(api_key)
    return api_key, provider_id, config


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


def _build_request(
    payload: Dict[str, Any],
    api_key: str,
    provider_id: str,
    config: Dict[str, Any],
    stream: bool,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """根据 api_format 构建统一的请求体和 headers"""
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
            "stream": stream,
        }
        system = payload.get("system", "")
        if system:
            api_payload["system"] = system
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    return api_payload, headers


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


def _parse_api_error(status_code: int, body: bytes) -> str:
    """解析上游 API 错误，返回友好提示"""
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            if "error" in data and isinstance(data["error"], dict):
                msg = data["error"].get("message", "")
                if msg:
                    return msg
            msg = data.get("message", data.get("error", ""))
            if msg:
                return str(msg)
    except Exception:
        pass
    if status_code == 401:
        return "API Key 无效或已过期，请检查 .env 配置"
    if status_code == 403:
        return "没有权限访问该 API，请确认 Key 是否有相应权限"
    if status_code == 429:
        return "API 请求过于频繁，请稍后再试"
    if status_code >= 500:
        return "AI 服务商暂时不可用，请稍后再试"
    return f"AI 服务返回错误 (HTTP {status_code})"


def _handle_http_error(status_code: int, body: bytes) -> None:
    """统一处理 HTTP 错误并抛出 HTTPException"""
    detail = _parse_api_error(status_code, body)
    raise HTTPException(status_code=status_code, detail=detail)


def _handle_network_error(exc: Exception) -> None:
    """统一处理网络异常并抛出 HTTPException"""
    if isinstance(exc, httpx.TimeoutException):
        raise HTTPException(status_code=504, detail="API 请求超时")
    if isinstance(exc, httpx.ConnectError):
        raise HTTPException(status_code=502, detail=f"无法连接到 API: {exc}")
    raise HTTPException(status_code=502, detail=f"API 请求失败: {exc}")


async def stream_chat(
    payload: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """流式聊天 API 调用"""
    api_key, provider_id, config = _validate_and_detect_provider()
    stream = payload.get("stream", True)
    api_payload, headers = _build_request(payload, api_key, provider_id, config, stream)
    api_format = config.get("api_format", "openai")

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
                    _handle_http_error(response.status_code, err_body)

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

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            _handle_network_error(e)


async def chat_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """非流式聊天 API 调用"""
    api_key, provider_id, config = _validate_and_detect_provider()
    api_payload, headers = _build_request(payload, api_key, provider_id, config, stream=False)
    api_format = config.get("api_format", "openai")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                config["url"], json=api_payload, headers=headers
            )
            response.raise_for_status()
            result = response.json()

            # OpenAI 格式 → Anthropic 格式转换（非流式）
            if api_format == "openai" and "choices" in result:
                text = result["choices"][0]["message"]["content"]
                result = {
                    "id": result.get("id", "msg_proxy"),
                    "type": "message",
                    "role": "assistant",
                    "model": result.get("model", ""),
                    "content": [{"type": "text", "text": text}],
                    "stop_reason": "end_turn",
                }

            return result
        except httpx.HTTPStatusError as e:
            body = await e.response.aread()
            _handle_http_error(e.response.status_code, body)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            _handle_network_error(e)


def get_health_info() -> Dict[str, Any]:
    """获取健康检查信息"""
    settings = get_settings()
    api_key = settings.anthropic_api_key

    if not api_key:
        return {
            "status": "ok",
            "api_configured": False,
            "provider": "未检测",
            "provider_id": "unknown",
            "default_model": "N/A",
            "supports_vision": False,
            "models": [],
        }

    try:
        provider_id, config = detect_provider(api_key)
        return {
            "status": "ok",
            "api_configured": True,
            "provider": config["name"],
            "provider_id": provider_id,
            "default_model": config["default_model"],
            "supports_vision": config["supports_vision"],
            "models": config["models"],
        }
    except HTTPException:
        return {
            "status": "ok",
            "api_configured": True,
            "provider": "无法识别",
            "provider_id": "unknown",
            "default_model": "N/A",
            "supports_vision": False,
            "models": [],
        }
