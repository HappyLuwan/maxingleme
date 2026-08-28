"""
Chat Provider 抽象接口
======================
职责：定义骂醒文案生成器的通用接口（供 LocalProvider 实现）。
本小程序仅使用本地文案库，不涉及任何外部生成式服务。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """
    骂醒生成请求
    - user_input: 用户输入文本
    - style_key: 可选风格 key（由业务层动态注入到本对象，pydantic 会容忍额外字段）
    """
    system_prompt: Optional[str] = None
    user_input: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    style_key: Optional[str] = None

    model_config = {"extra": "allow"}


class ChatResponse(BaseModel):
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_millis: Optional[int] = None


class AIProvider(ABC):
    """文案 Provider 抽象接口（命名保留 AI 前缀以兼容既有 import）"""

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