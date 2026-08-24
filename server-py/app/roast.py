"""
骂醒核心业务 + FastAPI 路由
对应 Java 的 RoastService + RoastController
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.base import ChatRequest
from app.ai.router import router as ai_router
from app.common import BusinessException, ErrorCode, Result
from app.enums import MVP_ENABLED, RoastStyle
from app.prompts import get_prompt
from app.repository import RoastRecord, repo
from app.security import check_content

logger = logging.getLogger(__name__)


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
def roast(request: RoastRequestDTO) -> RoastResponseDTO:
    """一键骂醒：参数校验 → 敏感词过滤 → 调用 AI → 保存记录 → 返回"""
    user_input = (request.user_input or "").strip()
    if not user_input:
        raise BusinessException(ErrorCode.CONTENT_EMPTY, "说点啥呀，别憋着")

    # 敏感词过滤
    check = check_content(user_input)
    if not check.passed:
        raise BusinessException(ErrorCode.CONTENT_ILLEGAL, check.message or "内容不合规")

    # 解析风格
    style = RoastStyle.from_key(request.style)

    # 自定义风格：不调用 AI，用户输入即为最终文案
    if style == RoastStyle.CUSTOM:
        record = RoastRecord(
            roast_id="",
            user_input=user_input,
            content=user_input,
            style=style,
            openid=request.openid,
            provider="custom",
        )
        record = repo.save(record)
        logger.info(
            "[Roast] custom id=%s len=%d", record.roast_id, len(user_input)
        )
        return RoastResponseDTO(
            roast_id=record.roast_id,
            content=user_input,
            style=style.key,
            style_name=style.display_name,
            style_emoji=style.emoji,
            provider="custom",
            cost_millis=0,
        )

    prompt = get_prompt(style)

    # 调用 AI
    chat_req = ChatRequest(
        system_prompt=prompt.system_prompt,
        user_input=user_input,
        temperature=prompt.temperature,
        max_tokens=prompt.max_tokens,
    )
    chat_resp = ai_router.chat(chat_req)
    if not chat_resp.content:
        raise BusinessException(ErrorCode.AI_RESPONSE_INVALID, "AI 返回内容为空")

    # 保存记录
    record = RoastRecord(
        roast_id="",
        user_input=user_input,
        content=chat_resp.content,
        style=style,
        openid=request.openid,
        provider=chat_resp.provider,
    )
    record = repo.save(record)
    logger.info(
        "[Roast] success id=%s style=%s provider=%s cost=%sms",
        record.roast_id, style.key, chat_resp.provider, chat_resp.cost_millis,
    )

    return RoastResponseDTO(
        roast_id=record.roast_id,
        content=chat_resp.content,
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


# ---------- FastAPI Router ----------
router = APIRouter(prefix="/api/roast", tags=["roast"])


@router.post("", response_model=Result)
def api_roast(req: RoastRequestDTO):
    return Result.success(roast(req).model_dump(by_alias=True))


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
