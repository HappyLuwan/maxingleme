"""
数据脱敏工具：admin 后台展示用

原则：
- 默认脱敏视图（openid 只保留前后 4 位，长文本截断+敏感数字打码）
- 仅在 admin 明确带 ?full=1 时返回原文（同时要求 X-Admin-Token 二次校验通过）
- 前端展示层任何时候都不应该看到未脱敏的完整数据
"""
from __future__ import annotations

import re

# 手机号：11 位 1 开头
_RE_PHONE = re.compile(r"1[3-9]\d{9}")
# 18 位身份证（含末位 X）
_RE_IDCARD = re.compile(r"\b\d{17}[\dXx]\b")
# 邮箱
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# 微信号：wx 开头 3-19 字母数字下划线（仅粗略识别，避免误伤）
_RE_WXID = re.compile(r"\bwx[a-zA-Z0-9_-]{5,20}\b")
# QQ 号：5-11 位纯数字（保守，避免误杀订单号）
_RE_QQ = re.compile(r"\bqq[:：]?\s*\d{5,11}\b", re.IGNORECASE)
# 银行卡：13-19 位纯数字连号
_RE_BANKCARD = re.compile(r"\b\d{13,19}\b")


def mask_openid(openid: str | None) -> str:
    """
    openid 脱敏：'wx1234567890abcdef' → 'wx12****cdef'
    - 长度 < 8：返回 '***'
    - 长度 8-11：前 3 + **** + 末 3
    - 长度 >= 12：前 4 + **** + 末 4
    """
    if not openid:
        return "***"
    n = len(openid)
    if n < 8:
        return "***"
    if n < 12:
        return f"{openid[:3]}****{openid[-3:]}"
    return f"{openid[:4]}****{openid[-4:]}"


def mask_text(text: str | None, max_len: int = 60) -> str:
    """
    正文脱敏：
    1) 敏感数字：手机号/身份证/邮箱/微信号/QQ/银行卡 → ***
    2) 长文本截断为 max_len 字（末尾加 …）
    """
    if not text:
        return ""
    s = text
    s = _RE_IDCARD.sub("***", s)
    s = _RE_PHONE.sub("***", s)
    s = _RE_EMAIL.sub("***", s)
    s = _RE_WXID.sub("***", s)
    s = _RE_QQ.sub("***", s)
    s = _RE_BANKCARD.sub("***", s)
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s


def mask_text_full(text: str | None) -> str:
    """
    完整脱敏（不截断，仅打码敏感数字）—— 用于 admin 查看详情时的默认模式。
    真正的原文（full=1）由 admin.py 决定是否返回。
    """
    if not text:
        return ""
    s = text
    s = _RE_IDCARD.sub("***", s)
    s = _RE_PHONE.sub("***", s)
    s = _RE_EMAIL.sub("***", s)
    s = _RE_WXID.sub("***", s)
    s = _RE_QQ.sub("***", s)
    s = _RE_BANKCARD.sub("***", s)
    return s
