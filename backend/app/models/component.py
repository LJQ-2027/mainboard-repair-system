from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class ComponentMapEntry(Base):
    __tablename__ = "component_maps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project = Column(String(50), nullable=False)
    module = Column(String(50), nullable=False)
    component_json = Column(Text, nullable=False)  # JSON 字符串
    updated_at = Column(DateTime, default=datetime.utcnow)
