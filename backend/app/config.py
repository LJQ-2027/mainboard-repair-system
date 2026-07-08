"""应用配置 - 使用 Pydantic Settings 自动加载 .env 文件"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 优先加载项目根目录的 .env
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未定义的 env 变量
    )

    # API Key
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # JWT 签名密钥（必须独立设置，不可使用 API Key）
    secret_key: str = Field(default="", alias="SECRET_KEY")

    # CORS 配置（多个来源用逗号分隔）
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_methods: str = Field(default="GET,POST,PUT,DELETE", alias="CORS_METHODS")
    cors_headers: str = Field(default="*", alias="CORS_HEADERS")

    # 提供商选择
    ai_provider: Literal["kimi", "kimi-code", "anthropic", "deepseek"] = Field(
        default="kimi-code", alias="AI_PROVIDER"
    )

    # 模型选择
    ai_model: str = Field(default="kimi-k2-thinking", alias="AI_MODEL")

    # 数据库
    database_url: str = Field(default="", alias="DATABASE_URL")

    # 服务端点
    port: int = Field(default=8899, alias="PORT")
    host: str = "0.0.0.0"

    # 安全头部
    enable_hsts: bool = Field(default=False, alias="ENABLE_HSTS")
    hsts_max_age: int = Field(default=31536000, alias="HSTS_MAX_AGE")

    # 速率限制
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    # 日志与监控
    log_format: Literal["text", "json"] = Field(default="text", alias="LOG_FORMAT")
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    # 日志
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("secret_key", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY 必须设置且至少 32 个字符")
        return v

    def get_cors_origins(self) -> list[str]:
        """将逗号分隔的来源字符串解析为列表"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_cors_methods(self) -> list[str]:
        """将逗号分隔的方法字符串解析为列表"""
        return [method.strip() for method in self.cors_methods.split(",") if method.strip()]

    def get_cors_headers(self) -> list[str]:
        """将逗号分隔的请求头字符串解析为列表"""
        return [header.strip() for header in self.cors_headers.split(",") if header.strip()]

    @property
    def api_key(self) -> str:
        """兼容旧代码的 api_key 属性"""
        return self.anthropic_api_key


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（缓存避免重复读取 .env）"""
    return Settings()
