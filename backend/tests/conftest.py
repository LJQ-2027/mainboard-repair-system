"""Pytest 配置 - 测试环境初始化"""

import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试环境设置（必须提供符合安全要求的 SECRET_KEY）
os.environ["ANTHROPIC_API_KEY"] = "sk-kimi-test-key-for-tests"
os.environ["AI_PROVIDER"] = "kimi-code"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-at-least-32-characters-long"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["TESTING"] = "true"

# 必须在设置 TESTING 环境变量后再导入数据库模块
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎（内存模式）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """每个测试用例独立的会话（事务隔离）"""
    connection = db_engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """FastAPI 测试客户端，数据库依赖注入"""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]
