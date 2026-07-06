"""数据库迁移测试"""

import importlib.util
import os
from pathlib import Path

import pytest


ALEMBIC_DIR = Path(__file__).parent.parent / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"


def _load_migration_module(path: Path):
    """动态加载迁移脚本模块"""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alembic_ini_exists():
    """alembic.ini 配置文件应存在"""
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    assert alembic_ini.exists()
    content = alembic_ini.read_text(encoding="utf-8")
    assert "script_location" in content


def test_alembic_env_py_exists():
    """alembic/env.py 应存在并可加载"""
    env_py = ALEMBIC_DIR / "env.py"
    assert env_py.exists()


def test_baseline_migration_exists():
    """baseline migration 应存在且包含核心表"""
    migration_files = list(VERSIONS_DIR.glob("*.py"))
    assert len(migration_files) >= 1, "未找到迁移文件"

    baseline = migration_files[0]
    module = _load_migration_module(baseline)

    assert hasattr(module, "upgrade")
    assert hasattr(module, "downgrade")
    assert hasattr(module, "revision")

    # 检查源码中是否包含核心表
    source = baseline.read_text(encoding="utf-8")
    expected_tables = [
        "users",
        "diagnosis_records",
        "chat_sessions",
        "projects",
        "knowledge_base",
        "component_maps",
    ]
    for table in expected_tables:
        assert table in source, f"迁移脚本缺少表: {table}"
