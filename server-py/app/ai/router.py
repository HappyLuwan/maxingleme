"""
Router：本地文案库 Provider 注册中心
====================================
本小程序仅使用本地精选文案库（人工创作 + 关键词匹配），
不涉及任何外部生成式服务。

保留 Router 抽象层是为了保持 roast.py 上游流水（限流/校验/落库/日志）
的代码不变，以及便于未来扩展更多本地匹配策略。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.ai.base import AIProvider, ChatRequest, ChatResponse
from app.ai.local_provider import LocalProvider
from app.common import BusinessException, ErrorCode

logger = logging.getLogger(__name__)


class LineRouter:
    """本地文案 Router：只挂载 LocalProvider"""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {
            "local": LocalProvider(),
        }
        logger.info(
            "[LineRouter] 已注册 %d 个 Provider: %s",
            len(self._providers), list(self._providers.keys()),
        )

    def get_provider(self, key: str) -> Optional[AIProvider]:
        return self._providers.get(key) if key else None

    def list_providers(self) -> list[AIProvider]:
        return list(self._providers.values())

    def chat(self, request: ChatRequest) -> ChatResponse:
        """走 local provider"""
        p = self._providers["local"]
        if not p.is_available():
            raise BusinessException(
                ErrorCode.AI_ALL_PROVIDERS_FAILED, "本地文案库不可用"
            )
        return p.chat(request)

    def chat_with(self, provider_key: str, request: ChatRequest) -> ChatResponse:
        """指定 provider 调用（后台测试用）"""
        p = self.get_provider(provider_key)
        if p is None:
            raise BusinessException(
                ErrorCode.AI_PROVIDER_NOT_FOUND, f"Provider 不存在：{provider_key}"
            )
        return p.chat(request)


# 全局单例（对外接口保持不变，命名沿用 `router`）
router = LineRouter()
