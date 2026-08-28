"""
用户维度：历史 + 收藏 5 个接口
- GET  /api/history            分页历史列表
- DELETE /api/history/{id}     删除单条历史（同时解除收藏）
- POST /api/favorite/{id}      收藏
- DELETE /api/favorite/{id}    取消收藏
- GET  /api/favorites          分页收藏列表
所有接口通过 Depends(get_openid) 拿到当前用户身份。
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.common import BusinessException, ErrorCode, Result
from app.repository import FavoriteRecord, RoastRecord, repo
from app.user import get_openid

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api", tags=["user"])


def _record_to_dict(r: RoastRecord, is_fav: Optional[bool] = None) -> dict:
    """记录 → 前端 DTO"""
    d = {
        "roastId": r.roast_id,
        "userInput": r.user_input,
        "content": r.content,
        "style": r.style.key,
        "styleName": r.style.display_name,
        "styleEmoji": r.style.emoji,
        "provider": r.provider,
        "createdAt": int(r.created_at * 1000),  # 毫秒时间戳
    }
    if is_fav is not None:
        d["isFavorite"] = is_fav
    return d


# ---------- 历史 ----------
@router.get("/history", response_model=Result)
def api_list_history(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    openid: str = Depends(get_openid),
):
    records, total = repo.list_history(openid, page, size)
    # 一次查出这一页每条是否被收藏
    fav_set = set()
    for r in records:
        if repo.is_favorite(openid, r.roast_id):
            fav_set.add(r.roast_id)
    items = [_record_to_dict(r, is_fav=(r.roast_id in fav_set)) for r in records]
    return Result.success({
        "list": items,
        "total": total,
        "page": page,
        "size": size,
        "hasMore": page * size < total,
    })


@router.delete("/history/{roast_id}", response_model=Result)
def api_delete_history(
    roast_id: str,
    openid: str = Depends(get_openid),
):
    ok = repo.delete(openid, roast_id)
    if not ok:
        raise BusinessException(ErrorCode.CARD_ROAST_NOT_FOUND, "记录不存在或已被删除")
    return Result.success({"deleted": True})


# ---------- 收藏 ----------
@router.post("/favorite/{roast_id}", response_model=Result)
def api_add_favorite(
    roast_id: str,
    openid: str = Depends(get_openid),
):
    if repo.is_favorite(openid, roast_id):
        # 幂等：已收藏视为成功
        return Result.success({"favorited": True, "already": True})
    ok = repo.add_favorite(openid, roast_id)
    if not ok:
        raise BusinessException(ErrorCode.CARD_ROAST_NOT_FOUND, "记录不存在或已过期")
    return Result.success({"favorited": True, "already": False})


@router.delete("/favorite/{roast_id}", response_model=Result)
def api_remove_favorite(
    roast_id: str,
    openid: str = Depends(get_openid),
):
    ok = repo.remove_favorite(openid, roast_id)
    if not ok:
        # 幂等：未收藏也视为成功
        return Result.success({"favorited": False, "already": True})
    return Result.success({"favorited": False, "already": False})


@router.get("/favorites", response_model=Result)
def api_list_favorites(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    openid: str = Depends(get_openid),
):
    favs, total = repo.list_favorites(openid, page, size)
    items = []
    for f in favs:
        d = _record_to_dict(f.record, is_fav=True)
        d["favoritedAt"] = int(f.favorited_at * 1000)
        items.append(d)
    return Result.success({
        "list": items,
        "total": total,
        "page": page,
        "size": size,
        "hasMore": page * size < total,
    })


# ---------- 统计 ----------
@router.get("/user/stats", response_model=Result)
def api_user_stats(openid: str = Depends(get_openid)):
    """
    我的页面顶部小统计：
    - historyCount: 历史总数
    - favoriteCount: 收藏总数
    - todayCount: 今日已骂醒次数
    """
    _, history_total = repo.list_history(openid, 1, 1)
    _, fav_total = repo.list_favorites(openid, 1, 1)
    today = repo.get_daily_count(openid)
    return Result.success({
        "historyCount": history_total,
        "favoriteCount": fav_total,
        "todayCount": today,
    })
