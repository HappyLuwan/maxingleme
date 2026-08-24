"""
应用配置：AI Provider 配置、卡片配置、管理员配置等
对应 Java 版 application.yml + AIProperties + AIRuntimeConfig
"""
from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    """单个 AI Provider 配置"""
    enabled: bool = True
    api_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 1.0
    max_tokens: int = 500


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

    # ---------- AI ----------
    ai_active_provider: str = Field(default="deepseek", alias="AI_ACTIVE_PROVIDER")
    ai_fallback_provider: str = Field(default="hunyuan", alias="AI_FALLBACK_PROVIDER")
    ai_timeout_seconds: int = 30

    # DeepSeek
    deepseek_api_url: str = Field(
        default="https://api.deepseek.com/v1",
        alias="DEEPSEEK_API_URL",
    )
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    deepseek_enabled: bool = Field(default=True, alias="DEEPSEEK_ENABLED")

    # 混元
    hunyuan_api_url: str = Field(
        default="https://api.hunyuan.cloud.tencent.com/v1",
        alias="HUNYUAN_API_URL",
    )
    hunyuan_api_key: str = Field(default="", alias="HUNYUAN_API_KEY")
    hunyuan_model: str = Field(default="hunyuan-lite", alias="HUNYUAN_MODEL")
    hunyuan_enabled: bool = Field(default=True, alias="HUNYUAN_ENABLED")

    # 豆包
    doubao_api_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        alias="DOUBAO_API_URL",
    )
    doubao_api_key: str = Field(default="", alias="DOUBAO_API_KEY")
    doubao_model: str = Field(default="doubao-lite-4k", alias="DOUBAO_MODEL")
    doubao_enabled: bool = Field(default=False, alias="DOUBAO_ENABLED")

    # 通义千问
    qwen_api_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="QWEN_API_URL",
    )
    qwen_api_key: str = Field(default="", alias="QWEN_API_KEY")
    qwen_model: str = Field(default="qwen-turbo", alias="QWEN_MODEL")
    qwen_enabled: bool = Field(default=False, alias="QWEN_ENABLED")

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

    def provider_config(self, key: str) -> Optional[ProviderConfig]:
        """按 provider key 获取配置对象"""
        mapping = {
            "deepseek": ProviderConfig(
                enabled=self.deepseek_enabled,
                api_url=self.deepseek_api_url,
                api_key=self.deepseek_api_key,
                model=self.deepseek_model,
                temperature=1.0,
                max_tokens=500,
            ),
            "hunyuan": ProviderConfig(
                enabled=self.hunyuan_enabled,
                api_url=self.hunyuan_api_url,
                api_key=self.hunyuan_api_key,
                model=self.hunyuan_model,
                temperature=1.0,
                max_tokens=500,
            ),
            "doubao": ProviderConfig(
                enabled=self.doubao_enabled,
                api_url=self.doubao_api_url,
                api_key=self.doubao_api_key,
                model=self.doubao_model,
                temperature=1.0,
                max_tokens=500,
            ),
            "qwen": ProviderConfig(
                enabled=self.qwen_enabled,
                api_url=self.qwen_api_url,
                api_key=self.qwen_api_key,
                model=self.qwen_model,
                temperature=1.0,
                max_tokens=500,
            ),
        }
        return mapping.get(key)


# ---------- 全局单例 ----------
settings = Settings()


class RuntimeConfig:
    """
    运行时可变配置：当前启用的 provider
    对应 Java 的 AIRuntimeConfig（通过后台接口一键切换）
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
        self._active = key

    def switch_fallback(self, key: str) -> None:
        self._fallback = key


runtime = RuntimeConfig(
    active=settings.ai_active_provider,
    fallback=settings.ai_fallback_provider,
)
