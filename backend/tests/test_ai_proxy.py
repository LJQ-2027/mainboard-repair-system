"""AI 代理服务单元测试"""
import json
import pytest
from app.services import ai_proxy


def test_detect_provider_kimi_code():
    """sk-kimi- 前缀应识别为 Kimi Code"""
    provider_id, config = ai_proxy.detect_provider("sk-kimi-testkey123")
    assert config["name"] == "Kimi Code (订阅版)"
    assert config["supports_vision"] is True
    assert config["api_format"] == "anthropic"


def test_provider_has_all_fields():
    """每个提供商配置应包含必要字段"""
    for pid, config in ai_proxy.PROVIDERS.items():
        assert "name" in config
        assert "url" in config
        assert "models" in config
        assert "default_model" in config
        assert "supports_vision" in config
        assert "api_format" in config
        assert config["api_format"] in ("openai", "anthropic")


def test_build_openai_payload_text_only():
    """纯文本消息应正确构建 OpenAI payload"""
    payload = {
        "model": "deepseek-chat",
        "system": "你是维修专家",
        "messages": [{"role": "user", "content": "手机不开机"}],
        "max_tokens": 100,
        "temperature": 0.5,
        "stream": True,
    }
    result = ai_proxy._build_openai_payload(payload, "deepseek")
    assert result["model"] == "deepseek-chat"
    assert result["max_tokens"] == 100
    assert len(result["messages"]) == 2


def test_build_openai_payload_with_image():
    """含图片的消息应保留图片（视觉平台）"""
    payload = {
        "model": "moonshot-v1-vision-preview",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw=="}},
                {"type": "text", "text": "这是什么芯片？"}
            ]
        }],
        "max_tokens": 200,
        "stream": False,
    }
    result = ai_proxy._build_openai_payload(payload, "kimi")
    user_content = result["messages"][0]["content"]
    assert isinstance(user_content, list)
    assert user_content[0]["type"] == "image_url"


def test_build_openai_payload_no_vision():
    """非视觉平台应提取纯文本并提示"""
    payload = {
        "model": "deepseek-chat",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "xxx"}},
                {"type": "text", "text": "故障分析"}
            ]
        }],
        "stream": False,
    }
    result = ai_proxy._build_openai_payload(payload, "deepseek")
    assert "故障分析" in result["messages"][0]["content"]
    assert "不支持图片" in result["messages"][0]["content"]


def test_convert_text_content():
    """字符串 content 应直接返回"""
    assert ai_proxy._convert_anthropic_content_to_openai("hello", "deepseek") == "hello"


def test_health_info():
    """健康检查应返回正确字段"""
    info = ai_proxy.get_health_info()
    assert info["status"] == "ok"
    assert "provider" in info
    assert "supports_vision" in info
    assert isinstance(info["models"], list)


def test_kimi_code_models():
    """Kimi Code 模型列表应包含标准模型"""
    models = ai_proxy.PROVIDERS["kimi-code"]["models"]
    assert "kimi-for-coding" in models
    assert "kimi-k2-thinking" in models
