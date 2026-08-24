"""
内容安全服务：本地敏感词过滤 + 心理危机词汇引导
对应 Java 的 ContentSecurityService
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# 敏感词库（MVP 版）
_BLACKLIST = [
    # 政治、暴恐（示例，实际部署时应用完整词库）
    "习近平", "毛泽东", "共产党", "法轮功", "达赖",
    # 色情
    "做爱", "性交", "自慰",
    # 违法犯罪
    "自杀", "自残", "杀人", "吸毒", "毒品", "赌博",
    # 心理危机（需要专业干预）
    "想死", "不想活", "轻生", "跳楼", "割腕",
]

_CRISIS_WORDS = {"想死", "不想活", "轻生", "跳楼", "割腕", "自杀", "自残"}


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    crisis: bool = False
    hit_word: Optional[str] = None
    message: Optional[str] = None

    @classmethod
    def pass_(cls) -> "CheckResult":
        return cls(passed=True)

    @classmethod
    def block(cls, word: str) -> "CheckResult":
        return cls(
            passed=False, crisis=False, hit_word=word,
            message="话里带了不太合适的词，换个说法试试？",
        )

    @classmethod
    def crisis_result(cls, word: str) -> "CheckResult":
        return cls(
            passed=False, crisis=True, hit_word=word,
            message="看到你的话，我很担心你。请拨打 24 小时心理援助热线 400-161-9995，你不是一个人在扛。",
        )


def check_content(text: str) -> CheckResult:
    """检测用户输入是否安全"""
    if not text or not settings.content_security_enabled:
        return CheckResult.pass_()

    lower = text.lower()
    for word in _BLACKLIST:
        if word.lower() in lower:
            preview = text[:30]
            logger.warning("[ContentSecurity] 命中敏感词: %s, preview: %s", word, preview)
            if word in _CRISIS_WORDS:
                return CheckResult.crisis_result(word)
            return CheckResult.block(word)
    return CheckResult.pass_()
