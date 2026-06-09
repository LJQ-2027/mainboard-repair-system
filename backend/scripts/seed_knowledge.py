#!/usr/bin/env python3
"""知识库数据种子脚本 - 将 data/*.js 导入数据库"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, init_db
from app.models.knowledge import KnowledgeBaseEntry

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def seed():
    init_db()
    db = SessionLocal()

    # 尝试加载 JSON 或 JS 文件中的知识库数据
    json_file = os.path.join(DATA_DIR, "hardwareKnowledgeBase.json")
    if not os.path.exists(json_file):
        print("No hardwareKnowledgeBase.json found (data was already extracted to JS modules)")
        db.close()
        return

    with open(json_file, "r", encoding="utf-8") as f:
        kb = json.load(f)

    count = 0
    for key, module in kb.items():
        if key == "analysisMethods":
            continue  # 跳过分析方法（不是诊断条目）

        entry = KnowledgeBaseEntry(
            category=key,
            title=module.get("title", key),
            content=json.dumps(module, ensure_ascii=False),
            keywords=",".join(module.get("keywords", [])),
            source=module.get("source", ""),
        )
        db.add(entry)
        count += 1

    db.commit()
    db.close()
    print(f"Seeded {count} knowledge base entries into database")


if __name__ == "__main__":
    seed()
