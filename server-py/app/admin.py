"""
后台管理接口：AI 一键切换 + Provider 测试
对应 Java 的 AdminController

鉴权：请求头 X-Admin-Token 必须与 ADMIN_TOKEN 一致
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.ai.base import ChatRequest
from app.ai.router import router as ai_router
from app.common import BusinessException, ErrorCode, Result
from app.config import runtime, settings

router = APIRouter(prefix="/admin/ai", tags=["admin"])


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
    data = [
        {
            "key": p.key,
            "name": p.name,
            "available": p.is_available(),
            "isActive": p.key == active,
            "isFallback": p.key == fallback,
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
        system_prompt=dto.system_prompt or "你是一个测试用的 AI 助手，请用一句话回复。",
        user_input=dto.user_input or "Hello",
    )
    resp = ai_router.chat_with(dto.provider_key, chat_req)
    return Result.success(resp.model_dump())
