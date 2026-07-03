"""认证服务 - JWT + bcrypt 密码哈希"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User

# 密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def _get_secret_key(settings) -> str:
    """获取 JWT 签名密钥，生产环境必须独立设置且长度 >= 32"""
    secret = settings.secret_key
    if not secret or secret == "change-me-in-production":
        raise RuntimeError(
            "SECURITY ERROR: SECRET_KEY 未设置或仍为默认值。"
            "请在 .env 中设置一个至少 32 字符的随机字符串（如：openssl rand -base64 48），"
            "且不可与 ANTHROPIC_API_KEY 相同。"
        )
    if len(secret) < 32:
        raise RuntimeError(
            "SECURITY ERROR: SECRET_KEY 长度不足 32 字符。"
            "请在 .env 中设置一个至少 32 字符的随机字符串，且不可与 ANTHROPIC_API_KEY 相同。"
        )
    return secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    secret = _get_secret_key(settings)
    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    settings = get_settings()
    secret = _get_secret_key(settings)
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def get_optional_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db)
) -> User | None:
    """获取当前用户（可选），未登录时返回 None"""
    if token is None:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "superuser"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
