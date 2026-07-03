from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base, _now_utc


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), default="新会话")
    messages_json = Column(Text, default="[]")  # JSON 字符串
    created_at = Column(DateTime, default=_now_utc)
    updated_at = Column(DateTime, default=_now_utc, onupdate=_now_utc)
