"""
openid 用户识别：
- 生产环境：微信云托管会自动在 Header 里塞 x-wx-openid
- 本地开发：Header 缺失时使用 dev-anon 兜底 openid，方便调试
- 兼容前端手动传 X-Openid Header 的场景
"""
from __future__ import annotations

import logging

from fastapi import Header

logger = logging.getLogger(__name__)

# 本地/未识别情况下的兜底 openid（保证调试链路可跑）
_DEV_ANON_OPENID = "dev-anon"


def get_openid(
    x_wx_openid: str | None = Header(default=None, alias="X-WX-OPENID"),
    x_openid: str | None = Header(default=None, alias="X-Openid"),
) -> str:
    """
    从请求 Header 读取 openid：
    1) 云托管注入的 X-WX-OPENID（首选）
    2) 前端手动传的 X-Openid（本地开发用）
    3) 都没有则返回 dev-anon（不阻断请求，避免开发期卡壳）
    """
    openid = (x_wx_openid or x_openid or "").strip()
    if not openid:
        return _DEV_ANON_OPENID
    return openid


def is_anonymous(openid: str | None) -> bool:
    """判断是否为兜底/未登录用户"""
    return not openid or openid == _DEV_ANON_OPENID
