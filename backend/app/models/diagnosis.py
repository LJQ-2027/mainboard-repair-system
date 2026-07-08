from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base, _now_utc


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 匿名诊断时为空
    mode = Column(String(50), nullable=False)  # AI / 专业 / 历史
    symptom = Column(Text)
    result_text = Column(Text)
    structured_result = Column(Text)  # JSON 字符串
    ai_model = Column(String(50))
    has_image = Column(Boolean, default=False)
    project_model = Column(String(50))
    sop_session_id = Column(
        Integer, ForeignKey("diagnosis_sop_sessions.id"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=_now_utc)
