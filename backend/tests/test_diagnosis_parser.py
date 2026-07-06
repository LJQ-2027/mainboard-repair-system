"""诊断结果解析器测试"""

import pytest

from app.schemas.diagnosis import StructuredDiagnosis
from app.services.diagnosis_parser import (
    extract_structured_data,
    parse_diagnosis_result,
    structured_to_json,
)


def test_extract_structured_data_from_json_block():
    text = """
建议检查电源IC。

```json
{
  "fault_type": "不开机",
  "confidence": "high",
  "summary": "电源IC损坏导致不开机",
  "recommended_tests": ["测电池电压", "测开机电流"],
  "repair_actions": ["更换电源IC"],
  "warnings": ["注意防静电"],
  "references": ["经验"]
}
```
"""
    data = extract_structured_data(text)
    assert data["fault_type"] == "不开机"
    assert data["confidence"] == "high"
    assert data["recommended_tests"] == ["测电池电压", "测开机电流"]


def test_extract_structured_data_from_plain_json():
    text = '建议检查。{"fault_type": "无显示", "confidence": "medium"}'
    data = extract_structured_data(text)
    assert data["fault_type"] == "无显示"
    assert data["confidence"] == "medium"


def test_extract_structured_data_invalid_json():
    text = "建议检查。{invalid json}"
    data = extract_structured_data(text)
    assert data == {}


def test_extract_structured_data_no_json():
    text = "建议检查电源IC。"
    data = extract_structured_data(text)
    assert data == {}


def test_parse_diagnosis_result():
    text = """
建议检查电源IC。

```json
{
  "fault_type": "不开机",
  "confidence": "high",
  "summary": "电源IC损坏",
  "recommended_tests": ["测电压"],
  "repair_actions": ["换电源IC"],
  "warnings": [],
  "references": ["经验"]
}
```
"""
    display_text, structured = parse_diagnosis_result(text)
    assert "```json" not in display_text
    assert structured.fault_type == "不开机"
    assert structured.confidence == "high"
    assert structured.summary == "电源IC损坏"


def test_parse_diagnosis_result_partial_fields():
    text = '```json\n{"fault_type": "无显示"}\n```'
    display_text, structured = parse_diagnosis_result(text)
    assert structured.fault_type == "无显示"
    assert structured.recommended_tests == []


def test_structured_to_json():
    structured = StructuredDiagnosis(fault_type="不开机", confidence="high")
    json_str = structured_to_json(structured)
    assert '"fault_type": "不开机"' in json_str
    assert '"confidence": "high"' in json_str
