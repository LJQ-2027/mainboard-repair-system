"""数据库配置测试"""

import os

import pytest


def test_database_url_defaults_to_sqlite(monkeypatch):
    """未设置 DATABASE_URL 且非测试环境时，默认使用 SQLite"""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "false")

    # 必须清除设置缓存，并重新导入 database 模块以读取新配置
    from app.config import get_settings

    get_settings.cache_clear()

    import importlib
    from app import database

    importlib.reload(database)

    assert database.SQLALCHEMY_DATABASE_URL.startswith("sqlite:///")
    assert database.DB_PATH.endswith("mainboard.db")


def test_database_url_from_env(monkeypatch):
    """设置 DATABASE_URL 时，使用指定的 PostgreSQL 连接串"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("TESTING", "false")

    from app.config import get_settings

    get_settings.cache_clear()

    import importlib
    from unittest.mock import patch

    from app import database

    # 无需真实安装 psycopg2，mock 掉 engine 创建
    with patch("sqlalchemy.create_engine"):
        importlib.reload(database)

    assert database.SQLALCHEMY_DATABASE_URL == "postgresql://user:pass@localhost/db"
    assert database.DB_PATH == ""


def test_database_url_testing_uses_memory(monkeypatch):
    """测试环境始终使用内存 SQLite"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("TESTING", "true")

    from app.config import get_settings

    get_settings.cache_clear()

    import importlib
    from app import database

    importlib.reload(database)

    assert database.SQLALCHEMY_DATABASE_URL == "sqlite:///:memory:"
