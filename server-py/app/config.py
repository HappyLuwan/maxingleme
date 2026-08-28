"""
应用配置：卡片配置、管理员配置、内容安全等
========================================
本小程序仅使用本地精选文案库提供服务，不涉及任何外部生成式服务。
"""
from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    """兼容占位（历史签名），本地文案库不需要此配置"""
    enabled: bool = True


class Settings(BaseSettings):
    """全局配置（支持环境变量覆盖）"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---------- Server ----------
    port: int = Field(default=8080, alias="PORT")
    host: str = "0.0.0.0"

    # ---------- 文案生成 ----------
    # 唯一 provider：local（本地精选文案库，人工创作）
    ai_active_provider: str = Field(default="local", alias="AI_ACTIVE_PROVIDER")
    ai_fallback_provider: str = Field(default="local", alias="AI_FALLBACK_PROVIDER")
    ai_timeout_seconds: int = 30

    # ---------- 卡片 ----------
    card_output_dir: str = Field(default="/tmp/mxlm-cards", alias="CARD_OUTPUT_DIR")
    card_width: int = 750
    card_height: int = 1000
    card_playwright_enabled: bool = Field(
        default=True, alias="CARD_PLAYWRIGHT_ENABLED"
    )

    # ---------- 管理后台 ----------
    admin_token: str = Field(default="mxlm-admin-2026", alias="ADMIN_TOKEN")

    # ---------- 内容安全 ----------
    content_security_enabled: bool = True
    # 微信 msgSecCheck 兜底开关（云托管环境默认开启；本地开发建议关掉避免误报）
    wx_msg_sec_check_enabled: bool = Field(
        default=True, alias="WX_MSG_SEC_CHECK_ENABLED"
    )

    def provider_config(self, key: str) -> Optional[ProviderConfig]:
        """兼容旧接口，本地文案库不需要配置对象"""
        if key == "local":
            return ProviderConfig(enabled=True)
        return None


# ---------- 全局单例 ----------
settings = Settings()


class RuntimeConfig:
    """
    运行时配置：当前 provider（保留字段以兼容旧代码，实际永远是 local）
    """

    def __init__(self, active: str, fallback: str) -> None:
        self._active = active
        self._fallback = fallback

    @property
    def active(self) -> str:
        return self._active

    @property
    def fallback(self) -> str:
        return self._fallback

    def switch_active(self, key: str) -> None:
        # 只允许切到 local
        if key != "local":
            return
        self._active = key

    def switch_fallback(self, key: str) -> None:
        if key != "local":
            return
        self._fallback = key


runtime = RuntimeConfig(
    active="local",
    fallback="local",
)
