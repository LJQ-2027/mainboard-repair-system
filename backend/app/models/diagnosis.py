from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mode = Column(String(50), nullable=False)  # AI / 专业 / 历史
    symptom = Column(Text)
    result_text = Column(Text)
    structured_result = Column(Text)  # JSON 字符串
    ai_model = Column(String(50))
    has_image = Column(Boolean, default=False)
    project_model = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
