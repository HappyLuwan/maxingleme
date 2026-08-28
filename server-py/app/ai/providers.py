"""
Provider 兼容导出模块
======================
本小程序仅使用本地文案库（人工创作），不涉及任何外部生成式服务。
本文件仅保留 `build_provider` 工厂签名以兼容旧调用点，实际只会返回 LocalProvider。
"""
from __future__ import annotations

from typing import Optional

from app.ai.base import AIProvider
from app.ai.local_provider import LocalProvider


def build_provider(key: str, cfg=None, timeout_seconds: int = 0) -> Optional[AIProvider]:
    """
    兼容工厂：无论传什么 key，只返回 LocalProvider（除非明确非 local）。
    """
    if key == "local":
        return LocalProvider()
    return None