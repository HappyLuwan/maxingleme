"""
内容安全服务：本地敏感词过滤 + 心理危机词汇引导 + 微信 msgSecCheck 双保险

优先级：
1) 本地心理危机词库（命中直接给援助电话，不走 AI、不写库）
2) 本地敏感词黑名单（政治/色情/暴力/辱骂，命中直接拒绝）
3) 微信 msgSecCheck 官方内容安全接口（兜底，拦截长尾变体）

⚠️ msgSecCheck 免费但需要 openid，云托管环境下无需自管 access_token。
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

# ---------- 心理危机词库（Layer 1：明确、无误杀） ----------
# 命中后不是拒绝，而是给出援助电话；不走 AI、不写库
# ⚠️ 只放"高置信度"表达，避免误伤"笑死我了""该死"等日常吐槽
_CRISIS_WORDS = {
    # —— 明确自杀意图
    "想死", "我想死", "我要死", "要死了我", "想不开", "寻短见",
    "自杀", "轻生", "了结自己", "了结生命", "结束生命", "结束自己",
    "结束一切", "结束这一切", "一了百了", "以死解脱",
    # —— 自伤/自残
    "自残", "自伤", "割腕", "割脉", "自缢", "上吊",
    # —— 具体自杀方式
    "跳楼", "跳桥", "跳江", "跳河", "跳海", "烧炭", "安眠药自杀",
    # —— 无望感表达
    "不想活", "不想活了", "不想活着", "活不下去", "活着没意思",
    "活着好累", "生无可恋", "了无生趣",
    "想消失", "彻底消失", "从这个世界消失", "离开这个世界",
    # —— 抑郁+死亡组合（网络高频表达）
    "抑郁到想死", "抑郁死了想死", "emo到想死",
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
    source: Optional[str] = None  # local | wxapi

    @classmethod
    def pass_(cls) -> "CheckResult":
        return cls(passed=True)

    @classmethod
    def block(cls, word: str, source: str = "local") -> "CheckResult":
        return cls(
            passed=False, crisis=False, hit_word=word, source=source,
            message="话里带了不太合适的词，换个说法试试？",
        )

    @classmethod
    def crisis_result(cls, word: str) -> "CheckResult":
        return cls(
            passed=False, crisis=True, hit_word=word, source="local",
            message=(
                "看到你的话，我很担心你。请一定要联系专业的心理援助：\n"
                "· 全国心理援助热线 400-161-9995\n"
                "· 北京心理危机研究与干预中心 010-82951332\n"
                "· 你不是一个人在扛，一定会有人愿意听你说。"
            ),
        )


def check_content(text: str, openid: Optional[str] = None) -> CheckResult:
    """
    检测用户输入是否安全（双保险）：
    1) 本地危机词库（优先，给援助电话）
    2) 本地敏感词黑名单（快速拒绝）
    3) 微信 msgSecCheck（兜底，需要 openid；失败降级放行避免误杀）
    """
    if not text or not settings.content_security_enabled:
        return CheckResult.pass_()

    lower = text.lower()
    # 1) 优先检测心理危机词
    for word in _CRISIS_WORDS:
        if word.lower() in lower:
            logger.warning("[ContentSecurity] 心理危机词命中: %s", word)
            return CheckResult.crisis_result(word)

    # 2) 再检测其他敏感词
    for word in _BLACKLIST:
        if word in _CRISIS_WORDS:
            continue  # 已在上面处理
        if word.lower() in lower:
            preview = text[:30]
            logger.warning("[ContentSecurity] 命中本地敏感词: %s, preview: %s", word, preview)
            return CheckResult.block(word, source="local")

    # 3) 微信 msgSecCheck 兜底（仅在启用 + 有 openid 时）
    if settings.wx_msg_sec_check_enabled and openid:
        try:
            # 延迟导入避免循环依赖
            from app.wechat_security import check_by_wxapi

            wx_res = check_by_wxapi(text, openid)
            if wx_res is not None and not wx_res.passed:
                logger.warning(
                    "[ContentSecurity] msgSecCheck 拦截: label=%s suggest=%s",
                    wx_res.label, wx_res.suggest,
                )
                return CheckResult.block(
                    wx_res.label or "wxapi", source="wxapi",
                )
        except Exception as exc:  # noqa: BLE001
            # 兜底策略：微信 API 异常时**放行**，不影响主链路
            logger.warning("[ContentSecurity] msgSecCheck 异常，降级放行: %s", exc)

    return CheckResult.pass_()
