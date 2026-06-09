from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)  # 不开机 / 充电异常 / ...
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    keywords = Column(String(500))  # 逗号分隔的关键词
    source = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
