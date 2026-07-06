"""诊断结果解析器

从 AI 回复中提取结构化诊断信息。
"""

import json
import re
from typing import Any

from app.schemas.diagnosis import StructuredDiagnosis


# 要求 AI 输出结构化 JSON 的提示（附加在 system prompt 后）
_STRUCTURED_OUTPUT_PROMPT = """

## 结构化输出要求
请在回复末尾附加一段 JSON 格式的结构化诊断结果，使用如下格式：
```json
{
  "fault_type": "故障类型",
  "confidence": "high/medium/low",
  "summary": "一句话摘要",
  "recommended_tests": ["测试项1", "测试项2"],
  "repair_actions": ["维修动作1", "维修动作2"],
  "warnings": ["注意事项"],
  "references": ["参考来源"]
}
```
"""


def get_structured_prompt() -> str:
    """返回结构化输出提示"""
    return _STRUCTURED_OUTPUT_PROMPT


def _extract_json_block(text: str) -> dict[str, Any] | None:
    """从文本中提取 ```json 代码块"""
    pattern = r"```json\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """从文本中提取第一个 JSON 对象"""
    # 匹配最外层的大括号（简单实现）
    match = re.search(r"\{[\s\S]*?\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def extract_structured_data(text: str) -> dict[str, Any]:
    """从 AI 回复文本中提取结构化数据

    优先匹配 ```json 代码块，失败则尝试匹配普通 JSON 对象。
    """
    data = _extract_json_block(text)
    if data is not None:
        return data

    data = _extract_json_object(text)
    if data is not None:
        return data

    return {}


def _strip_json_block(text: str) -> str:
    """移除文本末尾的 JSON 代码块，用于展示"""
    return re.sub(r"\s*```json\s*[\s\S]*?\s*```\s*$", "", text).strip()


def parse_diagnosis_result(text: str) -> tuple[str, StructuredDiagnosis]:
    """解析 AI 回复，返回 (展示文本, 结构化结果)"""
    data = extract_structured_data(text)
    display_text = _strip_json_block(text)
    structured = StructuredDiagnosis(**data)
    return display_text, structured


def structured_to_json(structured: StructuredDiagnosis) -> str:
    """将结构化结果序列化为 JSON 字符串"""
    return json.dumps(structured.model_dump(), ensure_ascii=False)
