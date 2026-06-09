"""Pytest 配置 - 测试环境初始化"""

import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试环境设置
os.environ["ANTHROPIC_API_KEY"] = "sk-kimi-test-key-for-tests"
os.environ["AI_PROVIDER"] = "kimi-code"

# 确保数据库已初始化
from app.database import init_db
init_db()
