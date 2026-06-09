"""输入校验和敏感词过滤"""

import re

# 症状输入限制
MAX_SYMPTOM_LENGTH = 2000
MIN_SYMPTOM_LENGTH = 3
MAX_SYSTEM_PROMPT_LENGTH = 10000

# 基础敏感词列表（可根据需要扩展）
SENSITIVE_PATTERNS = [
    r"<script",         # 防 XSS
    r"javascript:",      # 防 JS 注入
    r"on\w+\s*=",        # 防事件注入
    r"DROP\s+TABLE",     # 防 SQL（虽然用 ORM）
    r"UNION\s+SELECT",
]

# 允许的诊断相关内容模式
ALLOWED_PATTERNS = [
    r"^[a-zA-Z0-9一-鿿\s\-_.,;:()（）【】《》?!？！，。、：；\-+]+$",
]


def validate_symptom(text: str) -> tuple[bool, str]:
    """校验故障现象输入，返回 (是否有效, 错误消息)"""
    if not text or not text.strip():
        return False, "故障现象不能为空"

    text = text.strip()

    if len(text) < MIN_SYMPTOM_LENGTH:
        return False, f"故障现象至少需要 {MIN_SYMPTOM_LENGTH} 个字符"

    if len(text) > MAX_SYMPTOM_LENGTH:
        return False, f"故障现象不能超过 {MAX_SYMPTOM_LENGTH} 个字符"

    # 检查敏感模式
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "输入包含不允许的内容"

    return True, ""


def validate_system_prompt(text: str) -> tuple[bool, str]:
    """校验系统 Prompt"""
    if len(text) > MAX_SYSTEM_PROMPT_LENGTH:
        return False, f"系统提示词不能超过 {MAX_SYSTEM_PROMPT_LENGTH} 个字符"
    return True, ""


def sanitize_input(text: str) -> str:
    """净化输入（移除潜在危险字符）"""
    # 移除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 限制特殊字符连续出现
    text = re.sub(r"([<>{}()\[\]]){4,}", r"\1\1\1", text)
    return text.strip()
