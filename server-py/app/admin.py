"""
后台管理接口：Provider 状态 + 概览 + 用户吐槽查询
鉴权：请求头 X-Admin-Token 必须与 ADMIN_TOKEN 一致
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.base import ChatRequest
from app.ai.local_provider import get_library_stats
from app.ai.router import router as ai_router
from app.common import BusinessException, ErrorCode, Result
from app.config import runtime, settings
from app.enums import CARD_TEMPLATES, RoastStyle
from app.mask import mask_openid, mask_text, mask_text_full
from app.repository import repo

router = APIRouter(prefix="/admin/ai", tags=["admin"])

# ---------- Provider 管理 ----------


def _check_auth(token: Optional[str]) -> None:
    if not token or token != settings.admin_token:
        raise BusinessException(ErrorCode.UNAUTHORIZED, "后台鉴权失败")


class SwitchDTO(BaseModel):
    provider_key: str = Field(alias="providerKey")
    model_config = {"populate_by_name": True}


class TestDTO(BaseModel):
    provider_key: str = Field(alias="providerKey")
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    user_input: Optional[str] = Field(default=None, alias="userInput")
    model_config = {"populate_by_name": True}


@router.get("/providers", response_model=Result)
def list_providers(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    _check_auth(x_admin_token)
    active = runtime.active
    fallback = runtime.fallback
    stats = get_library_stats()
    data = [
        {
            "key": p.key,
            "name": p.name,
            "available": p.is_available(),
            "isActive": p.key == active,
            "isFallback": p.key == fallback,
            "libraryTotal": stats["total"],
            "libraryByStyle": stats["byStyle"],
        }
        for p in ai_router.list_providers()
    ]
    return Result.success(data)


@router.post("/switch", response_model=Result)
def switch_provider(
    dto: SwitchDTO,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _check_auth(x_admin_token)
    if ai_router.get_provider(dto.provider_key) is None:
        raise BusinessException(ErrorCode.AI_PROVIDER_NOT_FOUND, "Provider 不存在")
    runtime.switch_active(dto.provider_key)
    return Result.success({
        "activeProvider": runtime.active,
        "fallbackProvider": runtime.fallback,
    })


@router.post("/switch-fallback", response_model=Result)
def switch_fallback(
    dto: SwitchDTO,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _check_auth(x_admin_token)
    runtime.switch_fallback(dto.provider_key)
    return Result.success({
        "activeProvider": runtime.active,
        "fallbackProvider": runtime.fallback,
    })


@router.post("/test", response_model=Result)
def test_provider(
    dto: TestDTO,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _check_auth(x_admin_token)
    chat_req = ChatRequest(
        system_prompt=dto.system_prompt or "测试提示：请用一句话回复。",
        user_input=dto.user_input or "Hello",
    )
    resp = ai_router.chat_with(dto.provider_key, chat_req)
    return Result.success(resp.model_dump())


# ---------- Admin 数据总览 / 吐槽查询（新增） ----------
admin_data_router = APIRouter(prefix="/admin", tags=["admin"])


def _style_meta(key: str) -> dict:
    if not key:
        return {"key": "", "name": "", "emoji": ""}
    for s in RoastStyle:
        if s.key.lower() == key.lower():
            return {"key": s.key, "name": s.display_name, "emoji": s.emoji}
    return {"key": key, "name": key, "emoji": ""}


@admin_data_router.get("/overview", response_model=Result)
def admin_overview(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """概览：总用户/总骂醒/今日骂醒/总收藏/今日新增用户"""
    _check_auth(x_admin_token)
    data = repo.overview()
    # 附带 provider 运行时信息，页面能一眼看到当前使用哪个文案库
    data["activeProvider"] = runtime.active
    data["fallbackProvider"] = runtime.fallback
    return Result.success(data)


@admin_data_router.get("/records", response_model=Result)
def admin_list_records(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    style: Optional[str] = Query(default=None),
    favorited: bool = Query(default=False),
    days: int = Query(default=0, ge=0, le=365, description="仅查最近 N 天，0 表示全部"),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """用户吐槽列表（脱敏视图，用于 admin 页表格）"""
    _check_auth(x_admin_token)
    since_ts = None
    if days > 0:
        since_ts = datetime.now().timestamp() - days * 86400

    rows, total = repo.admin_list_records(
        page=page,
        size=size,
        style=style if style else None,
        favorited_only=favorited,
        since_ts=since_ts,
    )

    # 输出脱敏视图 + 元数据
    masked = []
    for r in rows:
        masked.append({
            "roastId": r["roastId"],
            "openidMasked": mask_openid(r["openid"]),
            "userInputPreview": mask_text(r["userInput"], max_len=50),
            "contentPreview": mask_text(r["content"], max_len=50),
            "style": _style_meta(r["style"]),
            "provider": r.get("provider"),
            "createdAt": r["createdAt"],
        })

    return Result.success({
        "page": page,
        "size": size,
        "total": total,
        "hasMore": page * size < total,
        "list": masked,
    })


@admin_data_router.get("/records/{roast_id}", response_model=Result)
def admin_get_record(
    roast_id: str,
    full: int = Query(default=0, description="1=返回未截断的完整文本（仍会打码手机号等敏感数字）"),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """单条详情：默认脱敏，full=1 时展示完整文本（仍打码手机号/身份证等）"""
    _check_auth(x_admin_token)
    row = repo.admin_get_record(roast_id)
    if not row:
        raise BusinessException(ErrorCode.NOT_FOUND, "记录不存在或已被删除")

    if full == 1:
        user_input = mask_text_full(row["userInput"])
        content = mask_text_full(row["content"])
    else:
        user_input = mask_text(row["userInput"], max_len=200)
        content = mask_text(row["content"], max_len=200)

    return Result.success({
        "roastId": row["roastId"],
        "openidMasked": mask_openid(row["openid"]),
        "userInput": user_input,
        "content": content,
        "style": _style_meta(row["style"]),
        "provider": row.get("provider"),
        "createdAt": row["createdAt"],
        "favoriteCount": row["favoriteCount"],
        "isFullMode": full == 1,
    })


@admin_data_router.get("/meta", response_model=Result)
def admin_meta(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """页面初始化用：风格列表 / 卡片模板列表（做筛选下拉框）"""
    _check_auth(x_admin_token)
    styles = [
        {"key": s.key, "name": s.display_name, "emoji": s.emoji}
        for s in RoastStyle
    ]
    templates = [
        {"key": k, "name": t.display_name}
        for k, t in CARD_TEMPLATES.items()
    ]
    return Result.success({"styles": styles, "templates": templates})