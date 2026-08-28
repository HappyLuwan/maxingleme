"""
卡片埋点接口：
- POST /api/track/card        前端上报（save / share），需 openid
- GET  /admin/card/stats      后台查询各模板事件汇总（需 X-Admin-Token）

generate 事件由后端 card.py 自动埋，前端只需负责 save / share。
埋点写库失败静默降级，绝不阻塞主链路。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field

from app.common import BusinessException, ErrorCode, Result
from app.config import settings
from app.enums import CARD_TEMPLATES
from app.repository import repo
from app.user import get_openid

logger = logging.getLogger(__name__)

# ---------- 前端上报 ----------
api_router = APIRouter(prefix="/api/track", tags=["analytics"])


class CardEventDTO(BaseModel):
    roast_id: Optional[str] = Field(default=None, alias="roastId")
    template: str
    event: str  # save / share（generate 由后端自动埋，前端不需要报）

    model_config = {"populate_by_name": True}


@api_router.post("/card", response_model=Result)
def api_track_card(dto: CardEventDTO, openid: str = Depends(get_openid)):
    # 只允许前端上报 save / share；generate 由后端 card.py 自己埋
    if dto.event not in ("save", "share"):
        raise BusinessException(ErrorCode.PARAM_ERROR, "event 仅支持 save / share")
    if dto.template not in CARD_TEMPLATES:
        raise BusinessException(ErrorCode.PARAM_ERROR, "template 非法")
    ok = repo.log_card_event(
        template=dto.template,
        event=dto.event,
        openid=openid,
        roast_id=dto.roast_id,
    )
    # 即使写库失败也返回 success，前端不需要感知
    return Result.success({"tracked": ok})


# ---------- 后台查询 ----------
admin_router = APIRouter(prefix="/admin/card", tags=["admin"])


def _check_auth(token: Optional[str]) -> None:
    if not token or token != settings.admin_token:
        raise BusinessException(ErrorCode.UNAUTHORIZED, "后台鉴权失败")


@admin_router.get("/stats", response_model=Result)
def admin_card_stats(
    days: int = Query(default=7, ge=1, le=365),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """
    近 N 天各模板卡片事件汇总。
    返回结构（按 generate 数降序）：
    [
      {"template": "tarot", "generate": 120, "save": 30, "share": 12,
       "saveRate": 0.25, "shareRate": 0.10},
      ...
    ]
    """
    _check_auth(x_admin_token)
    data = repo.stats_by_template(days=days)
    # 补齐 name（前端展示用）
    for row in data:
        tpl = CARD_TEMPLATES.get(row["template"])
        row["templateName"] = tpl.display_name if tpl else row["template"]
    return Result.success({
        "days": days,
        "list": data,
    })
