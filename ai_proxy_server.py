#!/usr/bin/env python3
"""
AI 代理服务器 - 智能主板维修系统
自动识别 API Key 类型，支持 Anthropic Claude 和 DeepSeek
端口: 8899
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

PORT = 8899

# 提供商配置
PROVIDERS = {
    "anthropic": {
        "name": "Anthropic Claude",
        "url": "https://api.anthropic.com/v1/messages",
        "key_prefix": "sk-ant-api03-",
        "models": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
        "default_model": "claude-sonnet-4-6",
    },
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/chat/completions",
        "key_prefix": "sk-",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
}


def detect_provider(api_key):
    """根据 API Key 前缀自动识别提供商"""
    for provider_id, config in PROVIDERS.items():
        if api_key.startswith(config["key_prefix"]):
            return provider_id, config
    # 默认当作 DeepSeek/OpenAI 兼容
    return "deepseek", PROVIDERS["deepseek"]


def convert_to_anthropic_sse(openai_chunk):
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


def extract_text_from_content(content):
    """从 Anthropic 内容块中提取纯文本（去掉图片）"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
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
            text += "\n\n[注意：用户上传了原理图截图，但当前使用的是 DeepSeek API 不支持图片分析。建议使用 Anthropic Claude API 以启用原理图视觉分析功能。]"
        return text
    return str(content)


def build_openai_payload(anthropic_payload):
    """将 Anthropic 格式的请求转为 OpenAI 格式，处理图片内容"""
    messages = []

    system = anthropic_payload.get("system", "")
    if system:
        messages.append({"role": "system", "content": system})

    for msg in anthropic_payload.get("messages", []):
        content = msg.get("content", "")
        # 提取纯文本（处理 content blocks 中有图片的情况）
        text_content = extract_text_from_content(content)
        messages.append({"role": msg.get("role", "user"), "content": text_content})

    return {
        "model": anthropic_payload.get("model", "deepseek-chat"),
        "messages": messages,
        "max_tokens": anthropic_payload.get("max_tokens", 4096),
        "temperature": anthropic_payload.get("temperature", 0.7),
        "stream": anthropic_payload.get("stream", True),
    }


def build_anthropic_response(text, model):
    """将文本构建为 Anthropic 格式的响应"""
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
                "supports_vision": provider_id == "anthropic",
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
        print(f"[DETECT] API Key → {config['name']} ({provider_id})")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "请求体不是有效的 JSON")
            return

        stream = payload.get("stream", True)

        if provider_id == "deepseek":
            # 转 Anthropic 格式 → OpenAI 格式
            api_payload = build_openai_payload(payload)
            api_url = config["url"]
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        else:
            # Anthropic 原生格式
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

            if stream and provider_id == "deepseek":
                self._handle_deepseek_stream(req)
            elif stream:
                self._handle_stream(req)
            elif provider_id == "deepseek":
                self._handle_deepseek_sync(req, api_payload["model"])
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

    def _handle_deepseek_sync(self, req, model):
        """DeepSeek 非流式 → 转 Anthropic 响应格式"""
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

    def _handle_stream(self, req):
        """Anthropic 流式 - 直接转发"""
        try:
            resp = urlopen(req, timeout=180)
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            buffer = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self.wfile.write(line + b"\n")
                    self.wfile.flush()
            if buffer:
                self.wfile.write(buffer)
                self.wfile.flush()
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            self._send_stream_error(f"API 返回错误: {err_body[:300]}")
        except URLError as e:
            self._send_stream_error(f"无法连接到 API: {e.reason}")

    def _handle_deepseek_stream(self, req):
        """DeepSeek 流式 → 转 Anthropic SSE 格式"""
        try:
            resp = urlopen(req, timeout=180)
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

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
                            self.wfile.write(b"data: {\"type\":\"message_stop\"}\n\n")
                            self.wfile.flush()
                            continue
                        converted = convert_to_anthropic_sse(data_str)
                        if converted:
                            self.wfile.write(f"data: {converted}\n\n".encode("utf-8"))
                            self.wfile.flush()
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            self._send_stream_error(f"API 返回错误: {err_body[:300]}")
        except URLError as e:
            self._send_stream_error(f"无法连接到 API: {e.reason}")

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

    def _send_error(self, code, message):
        self.send_response(code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        err = json.dumps({"error": message}, ensure_ascii=False)
        self.wfile.write(err.encode("utf-8"))


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    provider_id, config = detect_provider(api_key) if api_key else ("unknown", None)

    print("=" * 55)
    print("  AI 代理服务器 - 智能主板维修系统 v8.0")
    print("=" * 55)
    print(f"  监听地址: http://localhost:{PORT}")
    print(f"  健康检查: http://localhost:{PORT}/health")
    print(f"  API 端点: POST http://localhost:{PORT}/api/chat")
    print("-" * 55)
    if api_key:
        print(f"  识别平台: {config['name'] if config else '未知'}")
        print(f"  API Key : {api_key[:16]}...")
        print(f"  可用模型: {', '.join(config['models']) if config else 'N/A'}")
    else:
        print("  [WARNING] 未设置 ANTHROPIC_API_KEY 环境变量")
        print("  请在 .env 文件中配置 DeepSeek 或 Anthropic API Key")
    print("=" * 55)
    print("  支持平台: DeepSeek (sk-...) / Anthropic (sk-ant-api03-...)")
    print("  按 Ctrl+C 停止服务")
    print()

    server = HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
