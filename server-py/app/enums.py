"""
骂人风格枚举
对应 Java 的 RoastStyle
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class StyleMeta:
    key: str
    display_name: str
    emoji: str
    description: str


class RoastStyle(Enum):
    YIJU = StyleMeta("yiju", "一针见血", "💥", "一句话骂醒你，字字暴击")
    YINYANG = StyleMeta("yinyang", "阴阳怪气", "😏", "阴阳怪气小天才")
    WENROU = StyleMeta("wenrou", "温柔姐姐", "🌸", "温柔知性，说到你心里去")
    LUXUN = StyleMeta("luxun", "鲁迅式", "📜", "深刻犀利，字字诛心")
    ZHEXUE = StyleMeta("zhexue", "哲学家", "🌙", "从哲学高度让你顿悟")
    CUSTOM = StyleMeta("custom", "自定义", "✍️", "输入什么，卡片就是什么")

    @property
    def key(self) -> str:
        return self.value.key

    @property
    def display_name(self) -> str:
        return self.value.display_name

    @property
    def emoji(self) -> str:
        return self.value.emoji

    @property
    def description(self) -> str:
        return self.value.description

    @classmethod
    def from_key(cls, key: str | None) -> "RoastStyle":
        """根据 key 查找，找不到返回默认 YIJU"""
        if not key:
            return cls.YIJU
        for s in cls:
            if s.value.key.lower() == key.lower():
                return s
        return cls.YIJU


# MVP 阶段启用的风格（前端 style 选择器可用）
MVP_ENABLED = {
    RoastStyle.YIJU,
    RoastStyle.YINYANG,
    RoastStyle.WENROU,
    RoastStyle.LUXUN,
    RoastStyle.ZHEXUE,
    RoastStyle.CUSTOM,
}


@dataclass(frozen=True)
class CardTemplate:
    key: str
    display_name: str
    template_name: str  # 对应 templates/ 下的文件名


CARD_TEMPLATES: dict[str, CardTemplate] = {
    "punch": CardTemplate("punch", "金句海报", "card-punch.html"),
    "chat": CardTemplate("chat", "聊天截图", "card-chat.html"),
    "poster": CardTemplate("poster", "语录海报", "card-poster.html"),
}


def get_card_template(key: str | None) -> CardTemplate:
    """获取卡片模板，找不到返回默认 chat"""
    if not key:
        return CARD_TEMPLATES["chat"]
    return CARD_TEMPLATES.get(key.lower(), CARD_TEMPLATES["chat"])
