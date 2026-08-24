"""
AI Router：Provider 注册中心 + 自动 fallback
对应 Java 的 AIRouter
"""
from __future__ import annotations

import logging
from typing import Optional

from app.ai.base import AIProvider, ChatRequest, ChatResponse
from app.ai.providers import build_provider
from app.common import BusinessException, ErrorCode
from app.config import runtime, settings

logger = logging.getLogger(__name__)


class AIRouter:
    """AI 路由器：管理所有 Provider，根据 runtime 配置调度请求"""

    _PROVIDER_KEYS = ["deepseek", "hunyuan", "doubao", "qwen", "mock"]

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        for key in self._PROVIDER_KEYS:
            cfg = settings.provider_config(key)
            p = build_provider(key, cfg, settings.ai_timeout_seconds)
            if p is not None:
                self._providers[key] = p
        logger.info(
            "[AIRouter] 已注册 %d 个 Provider: %s",
            len(self._providers),
            list(self._providers.keys()),
        )

    def get_provider(self, key: str) -> Optional[AIProvider]:
        return self._providers.get(key) if key else None

    def list_providers(self) -> list[AIProvider]:
        return list(self._providers.values())

    def chat(self, request: ChatRequest) -> ChatResponse:
        """按 active provider 调用，失败自动 fallback"""
        active_key = runtime.active
        fallback_key = runtime.fallback

        # 1. 尝试 active
        try:
            provider = self.get_provider(active_key)
            if provider is not None and provider.is_available():
                return provider.chat(request)
            logger.warning("[AIRouter] active provider %s 不可用，尝试 fallback", active_key)
        except Exception as e:
            logger.error("[AIRouter] active provider %s 调用失败：%s", active_key, e)

        # 2. 尝试 fallback
        if fallback_key and fallback_key != active_key:
            try:
                fb = self.get_provider(fallback_key)
                if fb is not None and fb.is_available():
                    logger.info("[AIRouter] 使用 fallback provider: %s", fallback_key)
                    return fb.chat(request)
            except Exception as e:
                logger.error("[AIRouter] fallback provider %s 调用失败：%s", fallback_key, e)

        # 3. 兜底 mock（保证服务永远能返回结果）
        mock = self.get_provider("mock")
        if mock is not None:
            logger.warning("[AIRouter] 所有真实 Provider 都失败，降级到 Mock")
            return mock.chat(request)

        raise BusinessException(
            ErrorCode.AI_ALL_PROVIDERS_FAILED, "所有 AI Provider 都不可用"
        )

    def chat_with(self, provider_key: str, request: ChatRequest) -> ChatResponse:
        """指定 provider 调用（后台管理测试用）"""
        p = self.get_provider(provider_key)
        if p is None:
            raise BusinessException(
                ErrorCode.AI_PROVIDER_NOT_FOUND, f"Provider 不存在：{provider_key}"
            )
        if not p.is_available():
            raise BusinessException(
                ErrorCode.AI_PROVIDER_NOT_FOUND,
                f"Provider 未启用或配置不完整：{provider_key}",
            )
        return p.chat(request)


# 全局单例
router = AIRouter()
