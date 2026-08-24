"""
AI Provider 抽象基类 + 请求/响应模型
对应 Java 的 AIProvider / ChatRequest / ChatResponse / AbstractOpenAICompatibleProvider
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel

from app.common import BusinessException, ErrorCode
from app.config import ProviderConfig

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    system_prompt: Optional[str] = None
    user_input: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_millis: Optional[int] = None


class AIProvider(ABC):
    """AI Provider 抽象接口"""

    @property
    @abstractmethod
    def key(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse: ...


class OpenAICompatibleProvider(AIProvider):
    """
    OpenAI 协议兼容 Provider 基类
    DeepSeek / 混元 / 豆包 / 通义千问 全部支持 OpenAI 协议，只需换 base_url + api_key
    """

    def __init__(self, config: ProviderConfig, timeout_seconds: int = 30) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._client: Optional[OpenAI] = None

    def is_available(self) -> bool:
        cfg = self.config
        return (
            cfg is not None
            and cfg.enabled
            and bool(cfg.api_key)
            and not cfg.api_key.startswith("sk-your-")
            and not cfg.api_key.startswith("your-")
            and bool(cfg.api_url)
            and bool(cfg.model)
        )

    @staticmethod
    def _normalize_base_url(api_url: str) -> str:
        """
        兼容 "完整 URL" 和 "根 URL" 两种写法：
        - https://api.deepseek.com/v1/chat/completions -> https://api.deepseek.com/v1
        - https://api.deepseek.com/v1                   -> https://api.deepseek.com/v1
        """
        if not api_url:
            return api_url
        url = api_url.strip()
        if url.endswith("/chat/completions"):
            url = url[: -len("/chat/completions")]
        if url.endswith("/"):
            url = url[:-1]
        return url

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self._normalize_base_url(self.config.api_url),
                timeout=float(self.timeout_seconds),
            )
        return self._client

    def chat(self, request: ChatRequest) -> ChatResponse:
        if not self.is_available():
            raise BusinessException(
                ErrorCode.AI_PROVIDER_NOT_FOUND, f"{self.key} 未启用或配置不完整"
            )

        messages: list[dict] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_input})

        temperature = (
            request.temperature if request.temperature is not None else self.config.temperature
        )
        max_tokens = (
            request.max_tokens if request.max_tokens is not None else self.config.max_tokens
        )

        start = time.time()
        try:
            resp = self._get_client().chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except BusinessException:
            raise
        except Exception as e:
            logger.exception("[%s] OpenAI SDK 调用异常", self.key)
            raise BusinessException(
                ErrorCode.AI_CALL_FAILED, f"{self.key} 调用失败：{e}"
            ) from e

        content = ""
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            content = resp.choices[0].message.content.strip()

        usage = resp.usage
        return ChatResponse(
            content=content,
            model=self.config.model,
            provider=self.key,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            cost_millis=int((time.time() - start) * 1000),
        )
