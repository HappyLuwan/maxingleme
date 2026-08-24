"""
4 家 OpenAI 兼容 Provider + Mock Provider
对应 Java 的 DeepSeekProvider / HunyuanProvider / DoubaoProvider / QwenProvider / MockProvider
"""
from __future__ import annotations

import random
import time

from app.ai.base import AIProvider, ChatRequest, ChatResponse, OpenAICompatibleProvider
from app.config import ProviderConfig


class DeepSeekProvider(OpenAICompatibleProvider):
    @property
    def key(self) -> str:
        return "deepseek"

    @property
    def name(self) -> str:
        return "DeepSeek"


class HunyuanProvider(OpenAICompatibleProvider):
    @property
    def key(self) -> str:
        return "hunyuan"

    @property
    def name(self) -> str:
        return "腾讯混元"


class DoubaoProvider(OpenAICompatibleProvider):
    @property
    def key(self) -> str:
        return "doubao"

    @property
    def name(self) -> str:
        return "字节豆包"


class QwenProvider(OpenAICompatibleProvider):
    @property
    def key(self) -> str:
        return "qwen"

    @property
    def name(self) -> str:
        return "阿里通义千问"


class MockProvider(AIProvider):
    """
    Mock Provider：本地开发无 API Key 时使用，返回预置的骂醒文案
    """

    _MOCK_ROASTS = [
        "醒醒，你不是心动，是舍不得那些沉没成本。他要是真心，早就来了，不会等到现在来'找找看'。删了，别回。",
        "你不是在深思熟虑，你是在拖延。想了这么久，方向都没变，那就是不想改。要么就动，要么就闭嘴接受现状。",
        "别再自我感动了。你以为的坚持，在别人眼里只是消耗。清醒一点，不合适的东西，放下才是止损。",
        "你缺的不是道理，是行动。道理你都懂，就是不做。今晚就迈第一步，10 分钟也行。",
        "别把'舍不得'当'爱'。真正的爱是滋养你，不是让你怀疑自己。看清这一点，你就赢了一半。",
    ]

    @property
    def key(self) -> str:
        return "mock"

    @property
    def name(self) -> str:
        return "Mock（本地测试）"

    def is_available(self) -> bool:
        return True

    def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.time()
        # 模拟 300-800ms 延迟
        time.sleep(random.uniform(0.3, 0.8))
        content = random.choice(self._MOCK_ROASTS)
        return ChatResponse(
            content=content,
            model="mock",
            provider=self.key,
            prompt_tokens=len(request.user_input),
            completion_tokens=len(content),
            total_tokens=len(request.user_input) + len(content),
            cost_millis=int((time.time() - start) * 1000),
        )


def build_provider(key: str, cfg: ProviderConfig | None, timeout_seconds: int) -> AIProvider | None:
    """按 key 构造 Provider 实例（cfg 为 None 时返回 None）"""
    if key == "mock":
        return MockProvider()
    if cfg is None:
        return None
    if key == "deepseek":
        return DeepSeekProvider(cfg, timeout_seconds)
    if key == "hunyuan":
        return HunyuanProvider(cfg, timeout_seconds)
    if key == "doubao":
        return DoubaoProvider(cfg, timeout_seconds)
    if key == "qwen":
        return QwenProvider(cfg, timeout_seconds)
    return None
