"""
微信内容安全 API 封装：security.msgSecCheck

云托管特权：容器内访问 http://api.weixin.qq.com 会被微信透明代理签发合法凭证，
无需自管 AppSecret / access_token。

⚠️ 本地开发不在云托管环境时，msgSecCheck 调用会 401，因此上层已做异常降级放行。

官方文档：
https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/sec-center/sec-check/security.msgSecCheck.html
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 云托管场景：通过内网域名调用，无需 access_token
_WX_ENDPOINT_CLOUDBASE = "http://api.weixin.qq.com/wxa/msg_sec_check"
# 非云托管（含本地开发/自建部署）：走公网 + access_token（需自行维护）
_WX_ENDPOINT_PUBLIC = "https://api.weixin.qq.com/wxa/msg_sec_check"

# scene 取值：1=资料 2=评论 3=论坛 4=社交日志
# 我们的场景是用户吐槽输入文本 → 4（社交日志）最匹配
_DEFAULT_SCENE = 4
# version 固定 2（当前 API 版本）
_API_VERSION = 2
# 请求超时（秒）；msgSecCheck 服务端一般 <300ms
_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class WxCheckResult:
    passed: bool
    label: Optional[str] = None       # 违规类别（如 20001=广告 / 20006=违法违规）
    suggest: Optional[str] = None     # pass / review / risky
    trace_id: Optional[str] = None    # 微信侧的 trace_id，便于查问题


def _is_cloudbase_runtime() -> bool:
    """
    判断当前是否运行在微信云托管环境：
    云托管容器会自动注入 WX_INFRA_HOST 等环境变量；
    这里用最稳定的 X-WX-SERVICE 标识（云托管在响应头自带）来近似判断。
    保守起见，只要显式打开开关就走云托管 endpoint。
    """
    return os.environ.get("WX_CLOUDBASE", "").lower() in ("1", "true", "yes") \
        or os.environ.get("CBS_SERVICE_TYPE") is not None \
        or os.environ.get("TCB_ENV") is not None


def check_by_wxapi(content: str, openid: str) -> Optional[WxCheckResult]:
    """
    调用微信 msgSecCheck。
    返回：
      - WxCheckResult(passed=True)  → 内容安全
      - WxCheckResult(passed=False) → 命中违规
      - None → 调用失败/未启用，交由上层降级放行
    """
    if not content or not openid:
        return None
    if not settings.wx_msg_sec_check_enabled:
        return None

    # 云托管环境：无需 token，直接内网调用
    # 非云托管：如果配置了 access_token 获取方式再走公网（当前不实现，返回 None）
    if not _is_cloudbase_runtime():
        logger.debug("[WxSec] 非云托管环境，跳过 msgSecCheck")
        return None

    payload = {
        "version": _API_VERSION,
        "openid": openid,
        "scene": _DEFAULT_SCENE,
        "content": content,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.post(_WX_ENDPOINT_CLOUDBASE, json=payload)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("[WxSec] msgSecCheck 请求异常: %s", exc)
        return None

    errcode = data.get("errcode", -1)
    trace_id = data.get("trace_id")

    # errcode=0 表示接口调用成功（不代表内容通过，需看 result.suggest）
    if errcode == 0:
        result = data.get("result") or {}
        suggest = result.get("suggest", "pass")
        label = str(result.get("label", ""))
        passed = suggest == "pass"
        if not passed:
            logger.info(
                "[WxSec] 内容不通过 suggest=%s label=%s trace=%s",
                suggest, label, trace_id,
            )
        return WxCheckResult(
            passed=passed, label=label, suggest=suggest, trace_id=trace_id,
        )

    # 87014 = 内容含有违法违规内容（旧版直接错误码返回）
    if errcode == 87014:
        logger.info("[WxSec] errcode=87014 违规 trace=%s", trace_id)
        return WxCheckResult(
            passed=False, label="87014", suggest="risky", trace_id=trace_id,
        )

    # 其他错误码（40001 token 失效 / 45009 频率限制 等）→ 降级
    logger.warning(
        "[WxSec] msgSecCheck 返回异常 errcode=%s errmsg=%s trace=%s",
        errcode, data.get("errmsg"), trace_id,
    )
    return None
