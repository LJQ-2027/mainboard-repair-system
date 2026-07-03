"""数据库配置 - SQLAlchemy"""

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

# SQLite 数据库路径（默认在项目根目录）
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "mainboard.db")

# 测试环境使用内存数据库
TESTING = os.environ.get("TESTING", "").lower() == "true"
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:" if TESTING else f"sqlite:///{DB_PATH}"


def _now_utc() -> datetime:
    """返回当前 UTC 时间（带时区信息）"""
    return datetime.now(timezone.utc)


# 启用 WAL 模式提高并发性能
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.log_level == "DEBUG",
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """连接时启用 WAL 模式"""
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
