from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base, _now_utc


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    version = Column(String(50), default="")

    schematic_url = Column(String(500), default="")
    schematic_name = Column(String(200), default="")
    layout_url = Column(String(500), default="")
    layout_name = Column(String(200), default="")
    bom_url = Column(String(500), default="")
    bom_name = Column(String(200), default="")
    sop_url = Column(String(500), default="")
    sop_name = Column(String(200), default="")

    created_at = Column(DateTime, default=_now_utc)
    updated_at = Column(DateTime, default=_now_utc, onupdate=_now_utc)
