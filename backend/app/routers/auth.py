"""用户认证路由"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import rate_limit
from app.models.user import User
from app.schemas.user import LoginRequest, Token, UserCreate, UserResponse
from app.services.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
@rate_limit("5/minute")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    db_user = db.query(User).filter(User.username == user_in.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@rate_limit("10/minute")
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录 - 返回 JWT token"""
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(data={"sub": user.username})
    return Token(
        access_token=token,
        user=UserResponse(id=user.id, username=user.username, role=user.role),
    )


@router.get("/me", response_model=UserResponse)
@rate_limit("60/minute")
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
