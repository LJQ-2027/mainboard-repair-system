"""系统配置服务 - 数据库优先，.env 兜底

读取优先级：
  1. 数据库 system_config 表（加密存储）
  2. 环境变量 / .env 文件
"""

from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.utils.crypto import decrypt_value, encrypt_value

# 支持通过管理后台配置的 Key 列表
CONFIG_KEYS = {
    "ai_api_key": "AI 平台 API Key",
    "ai_provider": "AI 平台 (kimi-code / anthropic / deepseek / kimi)",
    "ai_model": "AI 模型名称",
}


def get_config(db: Session, key: str) -> str | None:
    """从数据库读取配置，不存在则返回 None"""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row and row.value:
        try:
            return decrypt_value(row.value)
        except Exception:
            return None
    return None


def set_config(db: Session, key: str, value: str, description: str = "") -> SystemConfig:
    """保存加密配置到数据库（如果 key 已存在则更新）"""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    encrypted = encrypt_value(value)
    if row:
        row.value = encrypted
        if description:
            row.description = description
    else:
        row = SystemConfig(key=key, value=encrypted, description=description)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_config(db: Session, key: str) -> bool:
    """删除配置项"""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        db.delete(row)
        db.commit()
        return True
    return False


def get_all_configs(db: Session) -> list[dict]:
    """列出所有配置项（值脱敏显示）"""
    rows = db.query(SystemConfig).order_by(SystemConfig.key).all()
    result = []
    for row in rows:
        masked = "已配置（加密存储）"
        desc = CONFIG_KEYS.get(row.key, {}).get("description", row.description or "")
        result.append({
            "key": row.key,
            "value": masked,
            "description": row.description or CONFIG_KEYS.get(row.key, ""),
            "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        })
    return result


def get_ai_api_key(db: Session | None) -> str | None:
    """获取 AI API Key（数据库优先，.env 兜底）"""
    if db is not None:
        db_key = get_config(db, "ai_api_key")
        if db_key:
            return db_key

    from app.config import get_settings
    settings = get_settings()
    return settings.anthropic_api_key or None


def get_ai_provider(db: Session | None) -> str | None:
    """获取 AI Provider（数据库优先，.env 兜底）"""
    if db is not None:
        db_provider = get_config(db, "ai_provider")
        if db_provider:
            return db_provider

    from app.config import get_settings
    settings = get_settings()
    return settings.ai_provider or None


def get_ai_model(db: Session | None) -> str | None:
    """获取 AI Model（数据库优先，.env 兜底）"""
    if db is not None:
        db_model = get_config(db, "ai_model")
        if db_model:
            return db_model

    from app.config import get_settings
    settings = get_settings()
    return settings.ai_model or None
