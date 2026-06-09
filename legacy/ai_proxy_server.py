#!/usr/bin/env python3
"""
AI 代理服务器 - 智能主板维修系统 v8.5
支持平台: Kimi Vision / Anthropic Claude / DeepSeek
- Kimi (moonshot):  视觉模型，支持原理图截图分析  ← 推荐
- Anthropic Claude: 视觉模型，支持原理图截图分析
- DeepSeek:         纯文本模型，不支持图片
端口: 8899
"""

import json
import os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.client import HTTPException

# ========== 自动加载 .env 文件 ==========
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    print(f"[ENV] 已加载 {_ENV_FILE}")
else:
    print(f"[WARN] 未找到 .env 文件: {_ENV_FILE}")
# =========================================

PORT = 8899

# ========== 提供商配置 ==========
PROVIDERS = {
    "kimi-code": {
        "name": "Kimi Code (订阅版)",
        "url": "https://api.kimi.com/coding/v1/messages",   # Kimi Code 订阅 API (Anthropic 格式)
        "key_prefix": "sk-kimi-",
        "models": [
            "kimi-for-coding",
            "kimi-k2-thinking",
            "kimi-k2-thinking-turbo",
        ],
        "default_model": "kimi-for-coding",
        "supports_vision": True,              # Kimi Code 支持视觉（kimi-k2-thinking 已测试通过）
        "api_format": "anthropic",            # Anthropic 兼容格式
    },
    "kimi": {
        "name": "Kimi (Moonshot)",
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "key_prefix": "sk-",
        "models": [
            "moonshot-v1-vision-preview",   # 视觉模型
            "moonshot-v1-128k",
            "moonshot-v1-32k",
            "moonshot-v1-8k",
        ],
        "default_model": "moonshot-v1-vision-preview",
        "supports_vision": True,
        "api_format": "openai",
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
# ==================================


def detect_provider(api_key):
    """
    检测 API 提供商:
    1. 优先使用 AI_PROVIDER 环境变量
    2. 根据 key 前缀自动识别
    """
    # 1. 手动指定 > 自动识别
    manual = os.environ.get("AI_PROVIDER", "").strip().lower()
    if manual and manual in PROVIDERS:
        return manual, PROVIDERS[manual]

    # 2. 根据 key 前缀匹配
    for provider_id, config in PROVIDERS.items():
        if api_key.startswith(config["key_prefix"]):
            # sk- 前缀同时匹配 kimi 和 deepseek
            # 如果 kimi 排在前面会优先匹配，所以将 deepseek 放最后
            # 用户可设 AI_PROVIDER 来精确控制
            return provider_id, config

    # 3. 默认 OpenAI 兼容 (deepseek)
    return "deepseek", PROVIDERS["deepseek"]


def convert_openai_sse_to_anthropic(openai_chunk):
    """将 OpenAI 格式的 SSE chunk 转为 Anthropic 格式"""
    try:
        data = json.loads(openai_chunk)
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
        return json.dumps({
            "type": "content_block_delta",
            "index": choice.get("index", 0),
            "delta": {"type": "text_delta", "text": content}
        }, ensure_ascii=False)

    return None


def convert_anthropic_content_to_openai(content, provider_id):
    """
    将 Anthropic 格式的 content 转为 OpenAI 兼容格式。
    - 文本: 直接保留
    - 图片: Anthropic 用 {"type":"image","source":{...}}
            → OpenAI 用 {"type":"image_url","image_url":{"url":"data:...;base64,..."}}
    - 如果平台不支持视觉，返回纯文本（去掉图片并加提示）
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        # 检查是否支持视觉
        provider = PROVIDERS.get(provider_id, {})
        supports_vision = provider.get("supports_vision", False)

        if not supports_vision:
            # 不支持视觉 → 提取纯文本
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
                text += "\n\n[注意：当前 API 不支持图片分析。建议切换到 Kimi Vision 或 Anthropic Claude 以启用原理图视觉分析功能。]"
            return text
        else:
            # 支持视觉 → 转换图片格式
            openai_blocks = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        openai_blocks.append({"type": "text", "text": block.get("text", "")})
                    elif block.get("type") == "image":
                        # Anthropic 格式 → OpenAI image_url 格式
                        source = block.get("source", {})
                        media_type = source.get("media_type", "image/png")
                        base64_data = source.get("data", "")
                        data_url = f"data:{media_type};base64,{base64_data}"
                        openai_blocks.append({
                            "type": "image_url",
                            "image_url": {"url": data_url}
                        })
            return openai_blocks

    return str(content)


def build_openai_compatible_payload(anthropic_payload, provider_id):
    """
    将 Anthropic 格式请求转为 OpenAI 兼容格式。
    支持 Kimi / DeepSeek / 任何 OpenAI 兼容 API。
    视觉平台保留图片数据。
    """
    messages = []

    system = anthropic_payload.get("system", "")
    if system:
        messages.append({"role": "system", "content": system})

    for msg in anthropic_payload.get("messages", []):
        content = msg.get("content", "")
        role = msg.get("role", "user")
        converted_content = convert_anthropic_content_to_openai(content, provider_id)
        messages.append({"role": role, "content": converted_content})

    config = PROVIDERS.get(provider_id, PROVIDERS["deepseek"])
    return {
        "model": anthropic_payload.get("model", config["default_model"]),
        "messages": messages,
        "max_tokens": anthropic_payload.get("max_tokens", 4096),
        "temperature": anthropic_payload.get("temperature", 0.7),
        "stream": anthropic_payload.get("stream", True),
    }


def build_anthropic_response(text, model):
    """将纯文本构建为 Anthropic 格式的响应"""
    return json.dumps({
        "id": "msg_proxy",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }, ensure_ascii=False)


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # ---- 静态文件服务：data/ 目录下的 JSON 文件 ----
        if self.path.startswith("/data/"):
            safe_path = self.path.replace("..", "").lstrip("/")
            file_path = os.path.join(os.path.dirname(__file__), safe_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "File not found"}).encode("utf-8"))
                return

        if self.path == "/health":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            provider_id, config = detect_provider(api_key) if api_key else (None, None)

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            resp = {
                "status": "ok",
                "api_configured": bool(api_key),
                "provider": config["name"] if config else "未检测",
                "provider_id": provider_id if config else "unknown",
                "default_model": config["default_model"] if config else "N/A",
                "supports_vision": config["supports_vision"] if config else False,
                "models": config["models"] if config else [],
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self._send_error(500, "未配置 ANTHROPIC_API_KEY 环境变量")
            return

        provider_id, config = detect_provider(api_key)
        print(f"[DETECT] API Key → {config['name']} ({provider_id}) | Vision: {config['supports_vision']}")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "请求体不是有效的 JSON")
            return

        stream = payload.get("stream", True)
        api_format = config.get("api_format", "openai")

        # ---- OpenAPI 兼容平台 (Kimi / DeepSeek) ----
        if api_format == "openai":
            api_payload = build_openai_compatible_payload(payload, provider_id)
            api_url = config["url"]
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # 打印是否包含图片
            has_image = False
            for msg in api_payload.get("messages", []):
                if isinstance(msg.get("content"), list):
                    for block in msg["content"]:
                        if block.get("type") == "image_url":
                            has_image = True
                            break
            if has_image:
                print(f"[API] → {config['name']} | model: {api_payload['model']} | stream: {stream} | [图片]")

        # ---- Anthropic 原生格式 ----
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
            api_url = config["url"]
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }

        print(f"[API] → {config['name']} | model: {api_payload['model']} | stream: {stream}")

        try:
            req = Request(
                api_url,
                data=json.dumps(api_payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            if api_format == "openai":
                if stream:
                    self._handle_openai_stream(req)
                else:
                    self._handle_openai_sync(req, api_payload["model"])
            else:
                if stream:
                    self._handle_stream(req)
                else:
                    self._handle_sync(req)

        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"[ERROR] API HTTP {e.code}: {err_body[:500]}")
            self._send_error(e.code, f"API 返回错误 ({e.code}): {err_body[:300]}")
        except URLError as e:
            print(f"[ERROR] 网络错误: {e.reason}")
            self._send_error(502, f"无法连接到 API: {e.reason}")
        except Exception as e:
            print(f"[ERROR] 未知错误: {e}")
            self._send_error(500, str(e))

    # ========== 流式处理 ==========

    def _handle_openai_stream(self, req):
        """OpenAI 兼容平台流式 → 转 Anthropic SSE 格式 (Kimi / DeepSeek)"""
        headers_sent = False
        try:
            resp = urlopen(req, timeout=180)
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            headers_sent = True

            buffer = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            try:
                                self.wfile.write(b'data: {"type":"message_stop"}\n\n')
                                self.wfile.flush()
                            except (BrokenPipeError, ConnectionResetError, OSError):
                                return
                            continue
                        converted = convert_openai_sse_to_anthropic(data_str)
                        if converted:
                            try:
                                self.wfile.write(f"data: {converted}\n\n".encode("utf-8"))
                                self.wfile.flush()
                            except (BrokenPipeError, ConnectionResetError, OSError):
                                return
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if not headers_sent:
                self._send_stream_error(f"API 返回错误: {err_body[:300]}")
            else:
                self._write_sse_error(f"API 返回错误: {err_body[:300]}")
        except URLError as e:
            if not headers_sent:
                self._send_stream_error(f"无法连接到 API: {e.reason}")
            else:
                self._write_sse_error(f"无法连接到 API: {e.reason}")
        except Exception as e:
            print(f"[STREAM ERROR] {type(e).__name__}: {e}")
            if not headers_sent:
                self._send_stream_error(f"流式传输错误: {str(e)}")
            else:
                self._write_sse_error(f"流式传输错误: {str(e)}")

    def _handle_stream(self, req):
        """Anthropic 流式 - 直接转发 SSE"""
        headers_sent = False
        try:
            resp = urlopen(req, timeout=180)
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            headers_sent = True

            buffer = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        self.wfile.write(line + b"\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        print("[INFO] 客户端断开连接")
                        return
            if buffer:
                try:
                    self.wfile.write(buffer)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if not headers_sent:
                self._send_stream_error(f"API 返回错误: {err_body[:300]}")
            else:
                self._write_sse_error(f"API 返回错误: {err_body[:300]}")
        except URLError as e:
            if not headers_sent:
                self._send_stream_error(f"无法连接到 API: {e.reason}")
            else:
                self._write_sse_error(f"无法连接到 API: {e.reason}")
        except Exception as e:
            print(f"[STREAM ERROR] {type(e).__name__}: {e}")
            if not headers_sent:
                self._send_stream_error(f"流式传输错误: {str(e)}")
            else:
                self._write_sse_error(f"流式传输错误: {str(e)}")

    # ========== 非流式处理 ==========

    def _handle_openai_sync(self, req, model):
        """OpenAI 兼容平台非流式 → 转 Anthropic 响应格式"""
        try:
            resp = urlopen(req, timeout=120)
            data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"]
            result = build_anthropic_response(text, model)
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode("utf-8"))
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            self._send_error(e.code, f"API 返回错误: {err_body[:300]}")
        except URLError as e:
            self._send_error(502, f"无法连接到 API: {e.reason}")

    def _handle_sync(self, req):
        """Anthropic 非流式"""
        try:
            resp = urlopen(req, timeout=120)
            data = resp.read()
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            self._send_error(e.code, f"API 返回错误: {err_body[:300]}")
        except URLError as e:
            self._send_error(502, f"无法连接到 API: {e.reason}")

    # ========== 错误处理 ==========

    def _send_stream_error(self, message):
        error_event = json.dumps({
            "type": "error",
            "error": {"message": message}
        }, ensure_ascii=False)
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(f"data: {error_event}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _write_sse_error(self, message):
        """向已打开的 SSE 流中写入错误事件，不修改 HTTP 状态码"""
        try:
            error_event = json.dumps({
                "type": "error",
                "error": {"message": message}
            }, ensure_ascii=False)
            self.wfile.write(f"data: {error_event}\n\n".encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass  # 客户端已断开，无法发送错误

    def _send_error(self, code, message):
        self.send_response(code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        err = json.dumps({"error": message}, ensure_ascii=False)
        self.wfile.write(err.encode("utf-8"))


# ========== 主函数 ==========

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    provider_id, config = detect_provider(api_key) if api_key else ("unknown", None)

    print("=" * 60)
    print("  AI 代理服务器 - 智能主板维修系统 v8.5")
    print("=" * 60)
    print(f"  监听地址:     http://localhost:{PORT}")
    print(f"  健康检查:     http://localhost:{PORT}/health")
    print(f"  API 端点:     POST http://localhost:{PORT}/api/chat")
    print("-" * 60)
    if api_key:
        print(f"  识别平台:     {config['name'] if config else '未知'}")
        print(f"  默认模型:     {config['default_model'] if config else 'N/A'}")
        print(f"  视觉分析:     {'[支持]' if config.get('supports_vision') else '[不支持]'}")
        print(f"  API Key :     {api_key[:16]}...")
    else:
        print("  [WARNING] 未设置 ANTHROPIC_API_KEY 环境变量")
        print("  请在 .env 文件中配置 API Key")
    print("-" * 60)
    print("  支持平台:")
    for pid, cfg in PROVIDERS.items():
        vision_icon = "[Vision]" if cfg["supports_vision"] else "[Text] "
        print(f"    {vision_icon} {cfg['name']:20s} ({cfg['key_prefix']}...)")
    print("=" * 60)
    print("  提示: .env 中设置 AI_PROVIDER=kimi 来指定平台")
    print("        按 Ctrl+C 停止服务")
    print()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
