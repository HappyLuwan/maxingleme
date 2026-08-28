"""
骂醒核心业务 + FastAPI 路由
对应 Java 的 RoastService + RoastController
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.ai.base import ChatRequest
from app.ai.router import router as ai_router
from app.common import BusinessException, ErrorCode, Result
from app.enums import MVP_ENABLED, RoastStyle
from app.prompts import get_prompt
from app.repository import DAILY_ROAST_LIMIT, RoastRecord, repo
from app.security import check_content
from app.user import get_openid, is_anonymous

logger = logging.getLogger(__name__)

# ---------- 长度控制 ----------
# 所有风格统一的硬上限（字符数，不区分中英文，1 emoji ≈ 1~2 char）
# 卡片 UI 面积、页面 8 行截断、朋友圈分享阅读时长综合考量下的黄金值
MAX_CONTENT_CHARS = 120

# 优先切分点：句末 → 分句 → 逗号
_SENTENCE_ENDS = ("。", "！", "？", "!", "?", ".", "…")
_SOFT_BREAKS = ("；", ";", "，", ",")


def _smart_truncate(text: str, limit: int = MAX_CONTENT_CHARS) -> str:
    """
    智能截断：优先在句末标点处截，其次在逗号处截，都找不到才硬截 + …。
    目标：让用户完全感知不到截断（读起来像 AI 本来就写这么多）。
    """
    if not text:
        return text
    s = text.strip()
    if len(s) <= limit:
        return s

    # 只在 [50%, 100%] 区间内找切分点，避免截得太短
    window_start = max(1, limit // 2)
    window = s[:limit]

    # 1) 优先句末标点
    best = -1
    for ch in _SENTENCE_ENDS:
        idx = window.rfind(ch)
        if idx >= window_start and idx > best:
            best = idx
    if best >= 0:
        return s[: best + 1]

    # 2) 退化到分句/逗号
    best = -1
    for ch in _SOFT_BREAKS:
        idx = window.rfind(ch)
        if idx >= window_start and idx > best:
            best = idx
    if best >= 0:
        return s[:best] + "。"

    # 3) 硬截 + 省略号
    return s[: limit - 1].rstrip() + "…"


# ---------- DTO ----------
class RoastRequestDTO(BaseModel):
    user_input: str = Field(alias="userInput")
    style: Optional[str] = "yiju"
    openid: Optional[str] = None

    model_config = {"populate_by_name": True}


class RoastResponseDTO(BaseModel):
    roast_id: str = Field(alias="roastId")
    content: str
    style: str
    style_name: str = Field(alias="styleName")
    style_emoji: str = Field(alias="styleEmoji")
    provider: Optional[str] = None
    cost_millis: Optional[int] = Field(default=None, alias="costMillis")

    model_config = {"populate_by_name": True}


# ---------- Service ----------
def roast(request: RoastRequestDTO, openid: str) -> RoastResponseDTO:
    """一键骂醒：限流 → 参数校验 → 敏感词过滤 → 匹配文案库 → 保存记录 → 返回"""
    user_input = (request.user_input or "").strip()
    if not user_input:
        raise BusinessException(ErrorCode.CONTENT_EMPTY, "说点啥呀，别憋着")

    # 每日限流：dev-anon 与实际用户都受限，防止滥用
    # 注意：先读后写，读时不占额，命中限流时不 +1
    used = repo.get_daily_count(openid)
    if used >= DAILY_ROAST_LIMIT:
        raise BusinessException(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            f"今日已骂醒 {used} 次，明天再来吧（每人每天上限 {DAILY_ROAST_LIMIT} 次）",
        )

    # 敏感词过滤 + 微信内容安全 API 双保险
    # 危机词与常规敏感词都走 CONTENT_ILLEGAL(1002)；前端根据 message 内容展示不同 UI
    check = check_content(user_input, openid=openid)
    if not check.passed:
        raise BusinessException(ErrorCode.CONTENT_ILLEGAL, check.message or "内容不合规")

    # 解析风格
    style = RoastStyle.from_key(request.style)

    # 优先 Header openid，其次 body 兼容
    effective_openid = openid if not is_anonymous(openid) else (request.openid or openid)

    # 自定义风格：不调用 AI，用户输入即为最终文案（同样做长度收敛，兜底）
    if style == RoastStyle.CUSTOM:
        final_content = _smart_truncate(user_input)
        record = RoastRecord(
            roast_id="",
            user_input=user_input,
            content=final_content,
            style=style,
            openid=effective_openid,
            provider="custom",
        )
        record = repo.save(record)
        repo.incr_daily_count(openid)
        logger.info(
            "[Roast] custom id=%s openid=%s len=%d",
            record.roast_id, _mask_openid(openid), len(final_content),
        )
        return RoastResponseDTO(
            roast_id=record.roast_id,
            content=final_content,
            style=style.key,
            style_name=style.display_name,
            style_emoji=style.emoji,
            provider="custom",
            cost_millis=0,
        )

    prompt = get_prompt(style)

    # 调用本地文案库（人工创作 + 关键词匹配）
    chat_req = ChatRequest(
        system_prompt=prompt.system_prompt,
        user_input=user_input,
        temperature=prompt.temperature,
        max_tokens=prompt.max_tokens,
        style_key=style.key,
    )
    chat_resp = ai_router.chat(chat_req)
    if not chat_resp.content:
        raise BusinessException(ErrorCode.AI_RESPONSE_INVALID, "文案库返回内容为空")

    # 智能截断：兵底，保证页面文案区和卡片图都不会视觉爆炸
    raw_len = len(chat_resp.content)
    final_content = _smart_truncate(chat_resp.content)
    if len(final_content) != raw_len:
        logger.info(
            "[Roast] truncated style=%s raw_len=%d final_len=%d",
            style.key, raw_len, len(final_content),
        )

    # 保存记录
    record = RoastRecord(
        roast_id="",
        user_input=user_input,
        content=final_content,
        style=style,
        openid=effective_openid,
        provider=chat_resp.provider,
    )
    record = repo.save(record)
    repo.incr_daily_count(openid)
    logger.info(
        "[Roast] success id=%s openid=%s style=%s provider=%s cost=%sms",
        record.roast_id, _mask_openid(openid), style.key, chat_resp.provider, chat_resp.cost_millis,
    )

    return RoastResponseDTO(
        roast_id=record.roast_id,
        content=final_content,
        style=style.key,
        style_name=style.display_name,
        style_emoji=style.emoji,
        provider=chat_resp.provider,
        cost_millis=chat_resp.cost_millis,
    )


def get_record(roast_id: str) -> RoastRecord:
    r = repo.find_by_id(roast_id)
    if r is None:
        raise BusinessException(ErrorCode.CARD_ROAST_NOT_FOUND, "骂醒记录不存在或已过期")
    return r


def _mask_openid(openid: str | None) -> str:
    """日志脱敏，防止全量 openid 落盘"""
    if not openid:
        return ""
    if len(openid) <= 8:
        return openid
    return openid[:4] + "***" + openid[-4:]


# ---------- FastAPI Router ----------
router = APIRouter(prefix="/api/roast", tags=["roast"])


@router.post("", response_model=Result)
def api_roast(req: RoastRequestDTO, openid: str = Depends(get_openid)):
    return Result.success(roast(req, openid).model_dump(by_alias=True))


@router.get("/quota", response_model=Result)
def api_get_quota(openid: str = Depends(get_openid)):
    """查询当日剩余骂醒次数"""
    used = repo.get_daily_count(openid)
    return Result.success({
        "used": used,
        "limit": DAILY_ROAST_LIMIT,
        "remaining": max(0, DAILY_ROAST_LIMIT - used),
    })


@router.get("/styles", response_model=Result)
def api_list_styles():
    styles = [
        {
            "key": s.key,
            "name": s.display_name,
            "emoji": s.emoji,
            "description": s.description,
            "enabled": s in MVP_ENABLED,
        }
        for s in RoastStyle
    ]
    return Result.success(styles)
