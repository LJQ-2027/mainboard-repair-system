"""系统配置加密存储

使用 AES-256-GCM 对敏感配置值（如 API Key）进行加密，
密钥派生自 SECRET_KEY（通过 SHA-256 哈希确保固定 32 字节）。

加密后的值格式: base64(nonce + ciphertext + tag)
"""

import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


def _derive_key() -> bytes:
    """从 SECRET_KEY 派生 32 字节 AES-256 密钥"""
    settings = get_settings()
    secret = settings.secret_key
    if not secret:
        raise RuntimeError("SECRET_KEY 未配置，无法进行加密操作")
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_value(plaintext: str) -> str:
    """加密字符串，返回 base64 编码的密文"""
    key = _derive_key()
    nonce = secrets.token_bytes(12)  # AES-GCM 推荐 12 字节 nonce
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # nonce + ciphertext（已含 16 字节 tag）
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_value(encrypted: str) -> str:
    """解密 base64 编码的密文，返回原始字符串"""
    key = _derive_key()
    raw = base64.b64decode(encrypted)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
