"""
内容安全服务：本地敏感词过滤 + 心理危机词汇引导
对应 Java 的 ContentSecurityService

⚠️ 注意：本地词库仅是最后一道兜底，正式上线时建议接入微信内容安全接口
(security.msgSecCheck) 做双重过滤。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ============ 分类敏感词库 ============
# 政治敏感（国家领导人、境外反华、分裂势力）—— 直接拒绝
_POLITICS = [
    "习近平", "毛泽东", "邓小平", "江泽民", "胡锦涛", "李克强", "温家宝",
    "共产党", "中央领导", "国家主席", "总书记",
    "法轮功", "达赖", "热比娅", "藏独", "疆独", "台独", "港独",
    "六四", "天安门事件", "文化大革命",
]

# 境外/宗教组织
_ORGS = [
    "邪教", "全能神", "东突", "伊斯兰国", "ISIS",
]

# 色情低俗
_PORN = [
    "做爱", "性交", "自慰", "口交", "肛交", "约炮", "一夜情",
    "卖淫", "嫖娼", "小姐服务", "援交",
]

# 违法犯罪（毒品、赌博、暴力）
_CRIME = [
    "吸毒", "毒品", "冰毒", "大麻", "海洛因", "摇头丸",
    "赌博", "赌场", "开设赌场", "网络赌博",
    "杀人", "爆炸", "恐怖袭击", "枪支", "军火",
    "洗钱", "传销",
]

# 心理危机（需要专业干预 —— 不是拒绝，而是给出援助电话）
_CRISIS_WORDS = {
    "想死", "不想活", "轻生", "跳楼", "割腕", "自杀", "自残",
    "结束生命", "活不下去", "了结自己", "上吊",
}

# 辱骂/人身攻击（避免 AI 被引导输出攻击性内容）
_INSULT = [
    "傻逼", "傻B", "sb", "cnm", "nmsl", "草泥马", "妈的",
    "去死", "滚蛋", "狗东西", "贱人", "婊子",
]

# 合并总词库
_BLACKLIST = _POLITICS + _ORGS + _PORN + _CRIME + list(_CRISIS_WORDS) + _INSULT


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
            message=(
                "看到你的话，我很担心你。请一定要联系专业的心理援助：\n"
                "· 全国心理援助热线 400-161-9995\n"
                "· 北京心理危机研究与干预中心 010-82951332\n"
                "· 你不是一个人在扛，一定会有人愿意听你说。"
            ),
        )


def check_content(text: str) -> CheckResult:
    """检测用户输入是否安全"""
    if not text or not settings.content_security_enabled:
        return CheckResult.pass_()

    lower = text.lower()
    # 优先检测心理危机词（给援助信息而非简单拒绝）
    for word in _CRISIS_WORDS:
        if word.lower() in lower:
            logger.warning("[ContentSecurity] 心理危机词命中: %s", word)
            return CheckResult.crisis_result(word)

    # 再检测其他敏感词
    for word in _BLACKLIST:
        if word in _CRISIS_WORDS:
            continue  # 已在上面处理
        if word.lower() in lower:
            preview = text[:30]
            logger.warning("[ContentSecurity] 命中敏感词: %s, preview: %s", word, preview)
            return CheckResult.block(word)
    return CheckResult.pass_()
