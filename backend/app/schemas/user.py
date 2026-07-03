import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_一-鿿]+$", v):
            raise ValueError("用户名只能包含字母、数字、下划线和中文")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """密码复杂度校验：至少包含大写、小写、数字、特殊字符中的两类"""
        has_upper = bool(re.search(r"[A-Z]", v))
        has_lower = bool(re.search(r"[a-z]", v))
        has_digit = bool(re.search(r"\d", v))
        has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", v))

        score = sum([has_upper, has_lower, has_digit, has_special])
        if score < 2:
            raise ValueError(
                "密码必须至少包含以下两类：大写字母、小写字母、数字、特殊字符"
            )
        return v


class UserResponse(UserBase):
    id: int
    role: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str
