"""
本地文案 Provider
==================
职责：
- 从预置文案库根据关键词标签匹配最贴合的文案返回
- 完全不涉及 AI 生成，所有文案均为人工创作
- 保留 AIProvider 接口以复用上层流水（router / roast.py）不改动

匹配算法（v2 加权评分模型）：
1. 关键词分权重：强主诉词=3、常规词=2、修饰词=1
2. 各 tag 累计得分，最高分者为"主诉 tag"
3. 文案打分：命中主诉 tag +10、命中次要 tag +3、多 tag 命中额外 bonus
4. 同分随机（避免"总是同一句"）
"""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

from app.ai.base import AIProvider, ChatRequest, ChatResponse
from app.ai.local_lines import (
    KEYWORD_TAG_MAP,
    LINES,
    extract_tags,
    get_lines_by_style,
    get_total_count,
)

logger = logging.getLogger(__name__)


# ============================================================
# 关键词权重表（未列出的默认 = 2）
# ============================================================
# 强主诉词（权重 3）：明确表达用户困扰的核心词
STRONG_KEYWORDS = {
    # love
    "分手", "复合", "劈腿", "出轨", "挽回", "冷战", "已读", "不回", "备胎",
    # work
    "辞职", "跳槽", "加班", "裁员", "背锅", "996", "内卷",
    # study
    "挂科", "补考", "论文", "答辩", "考研", "高考",
    # money
    "剁手", "月光", "破产", "花呗", "贷款",
    # sleep
    "失眠", "熬夜",
    # fit
    "减肥", "健身", "增肌",
    # eat
    "暴食", "戒糖", "夜宵",
    # family
    "催婚", "催生", "相亲",
    # social
    "拒绝不了", "讨好",
    # self
    "崩溃", "抑郁", "焦虑", "内耗", "废物", "不想活", "没意义",
    # delay
    "拖延", "摆烂", "躺平",
    # phone
    "上瘾", "刷视频", "短视频",
}
# 弱修饰词（权重 1）：可能只是场景描述，不是主诉
WEAK_KEYWORDS = {
    "凌晨", "深夜", "早睡", "起床", "起不来", "赖床",  # 修饰"睡眠场景"，不一定主诉是睡眠
    "累", "困", "想哭",  # 情绪描述，不一定主诉是self
    "手机", "屏幕",  # 太泛
    "过年", "回家",  # 修饰"时间/地点"
    "算了", "懒",  # 太泛
}
# 默认权重
DEFAULT_KEYWORD_WEIGHT = 2


def _score_tags(user_input: str) -> dict[str, int]:
    """
    对用户输入抽取 tag 并计算每个 tag 的得分。
    返回 {tag: score}
    """
    if not user_input:
        return {}
    text = user_input.lower()
    scores: dict[str, int] = {}
    for tag, keywords in KEYWORD_TAG_MAP.items():
        s = 0
        for kw in keywords:
            if kw.lower() in text:
                if kw in STRONG_KEYWORDS:
                    s += 3
                elif kw in WEAK_KEYWORDS:
                    s += 1
                else:
                    s += DEFAULT_KEYWORD_WEIGHT
        if s > 0:
            scores[tag] = s
    return scores


def _score_line(line_tags: list[str], primary_tag: str, secondary_tags: set[str]) -> int:
    """
    对候选文案打分：
    - 命中主诉 tag：+10
    - 每命中一个次要 tag：+3
    - 命中 tag 数量的 bonus：命中 2 个 +2、3 个及以上 +5
    """
    score = 0
    hit_count = 0
    for t in line_tags:
        if t == primary_tag:
            score += 10
            hit_count += 1
        elif t in secondary_tags:
            score += 3
            hit_count += 1
    # 多标签命中 bonus
    if hit_count >= 3:
        score += 5
    elif hit_count == 2:
        score += 2
    return score


class LocalProvider(AIProvider):
    """
    本地文案库 Provider（人工创作 + 加权评分匹配）
    """

    @property
    def key(self) -> str:
        return "local"

    @property
    def name(self) -> str:
        return "本地精选文案库"

    def is_available(self) -> bool:
        return get_total_count() > 0

    def chat(self, request: ChatRequest) -> ChatResponse:
        """
        入参 request：
            - user_input: 用户输入文本
            - style_key (动态属性)：风格 key，由 roast.py 传入
        出参 ChatResponse：
            - content: 匹配到的文案（长度已保证 <= 120）
            - provider: "local"
        """
        start = time.time()

        # 从动态属性拿 style_key（roast.py 会赋值），拿不到就用默认 yiju
        style_key = getattr(request, "style_key", None) or "yiju"
        style_key = style_key.lower()

        # 1) 抽取 tag 及各自得分
        tag_scores = _score_tags(request.user_input or "")

        # 2) 拿到该风格全部文案
        candidates = get_lines_by_style(style_key)

        primary_tag: Optional[str] = None
        secondary_tags: set[str] = set()
        pool: list[str] = []
        strategy = ""

        if tag_scores:
            # 3) 主诉 tag = 得分最高的（并列时取第一个）
            sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
            primary_tag = sorted_tags[0][0]
            secondary_tags = {t for t, _ in sorted_tags[1:]}

            # 4) 对候选文案打分，只保留得分 > 0 的
            scored: list[tuple[int, str]] = []
            for content, line_tags in candidates:
                s = _score_line(line_tags, primary_tag, secondary_tags)
                if s > 0:
                    scored.append((s, content))

            if scored:
                # 5) 取得分最高的一批（允许 top-tier 内随机，避免每次同一句）
                max_score = max(s for s, _ in scored)
                pool = [c for s, c in scored if s == max_score]
                strategy = f"top_score={max_score}"

        # 6) 兜底 1：如果没命中任何 tag 或打分全为 0，退化到 general 池
        if not pool:
            pool = [c for c, ts in candidates if "general" in ts]
            strategy = "fallback_general"

        # 7) 兜底 2：general 也没有（理论不会），从该风格全池随机
        if not pool:
            pool = [c for c, _ in candidates]
            strategy = "fallback_all"

        content = random.choice(pool)

        # 加一小段"思考时间"，避免响应快到反常
        time.sleep(random.uniform(0.2, 0.5))

        cost = int((time.time() - start) * 1000)
        logger.info(
            "[Local] style=%s tag_scores=%s primary=%s pool=%d strategy=%s cost=%dms",
            style_key, tag_scores, primary_tag, len(pool), strategy, cost,
        )

        return ChatResponse(
            content=content,
            model="local-v2",
            provider=self.key,
            prompt_tokens=len(request.user_input),
            completion_tokens=len(content),
            total_tokens=len(request.user_input) + len(content),
            cost_millis=cost,
        )


def get_library_stats() -> dict:
    """
    文案库统计（供后台管理页展示）
    """
    stats = {"total": get_total_count(), "byStyle": {}}
    for style_key, lines in LINES.items():
        stats["byStyle"][style_key] = len(lines)
    return stats