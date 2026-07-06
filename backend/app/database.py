"""数据库配置 - SQLAlchemy

支持 SQLite（开发/测试）和 PostgreSQL（生产）。
通过 DATABASE_URL 环境变量指定 PostgreSQL 连接串。
"""

import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

TESTING = os.environ.get("TESTING", "").lower() == "true"
DB_PATH = ""

if TESTING:
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
elif settings.database_url:
    SQLALCHEMY_DATABASE_URL = settings.database_url
else:
    # SQLite 数据库路径（默认在项目根目录）
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(DB_DIR, exist_ok=True)
    DB_PATH = os.path.join(DB_DIR, "mainboard.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"


def _now_utc() -> datetime:
    """返回当前 UTC 时间（带时区信息）"""
    return datetime.now(timezone.utc)


# 构建 engine 参数
_engine_kwargs = {
    "echo": settings.log_level == "DEBUG",
}

# SQLite 需要关闭同线程检查；PostgreSQL 不需要额外 connect_args
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)


if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        """SQLite 连接时启用 WAL 模式"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Depends 用数据库会话生成器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    from app import models  # noqa
    Base.metadata.create_all(bind=engine)
