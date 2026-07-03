from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base, _now_utc


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # user, admin, superuser
    created_at = Column(DateTime, default=_now_utc)
