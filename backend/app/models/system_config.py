"""系统配置模型 - 存储 API Key 等敏感配置（加密存储）"""

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base, _now_utc


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)  # 加密后的值
    description = Column(String(500), default="")
    updated_at = Column(DateTime, default=_now_utc, onupdate=_now_utc)
