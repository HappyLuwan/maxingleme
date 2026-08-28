"""
卡片生成服务 + FastAPI 路由
对应 Java 的 CardService + CardController
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field

from app.common import BusinessException, ErrorCode, Result
from app.config import settings
from app.enums import CARD_TEMPLATES, get_card_template
from app.playwright_pool import pool
from app.repository import repo
from app.roast import get_record
from app.user import get_openid

logger = logging.getLogger(__name__)

# ---------- 卡片装饰用：干支纪年 & 每日流水号 ----------
_TIANGAN = "甲乙丙丁戊己庚辛壬癸"
_DIZHI = "子丑寅卯辰巳午未申酉戌亥"

def _ganzhi_year(year: int) -> str:
    """公历年份 → 干支纪年（简化：以公历 1 月 1 日近似，跨立春误差可接受，卡片装饰用不做精算）"""
    # 公元 4 年是甲子年
    idx = (year - 4) % 60
    return _TIANGAN[idx % 10] + _DIZHI[idx % 12]

_serial_lock = threading.Lock()
_serial_state: dict = {"date": None, "count": 0}
# roastId → serialNo 映射，保证同一次骂醒的多套卡片共用同一个编号
_serial_by_roast: dict[str, str] = {}

def _next_serial_no(roast_id: str | None = None) -> str:
    """每日自增流水号，格式：No.001（跨日重置）。同一 roastId 复用同一个编号。"""
    if roast_id and roast_id in _serial_by_roast:
        return _serial_by_roast[roast_id]
    today = date.today()
    with _serial_lock:
        if _serial_state["date"] != today:
            _serial_state["date"] = today
            _serial_state["count"] = 0
            _serial_by_roast.clear()
        _serial_state["count"] += 1
        n = _serial_state["count"]
        serial = f"No.{n:03d}"
        if roast_id:
            _serial_by_roast[roast_id] = serial
    return serial


# ---------- 卡片装饰用：基于 roastId 的确定性伪数据 ----------
def _hash_ints(roast_id: str, salt: str, n: int) -> int:
    """基于 roastId+salt 生成 [0, n) 范围内的确定性整数（同一 roastId+salt 每次返回一致）"""
    if not roast_id:
        roast_id = "anon"
    h = hashlib.md5(f"{roast_id}|{salt}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) % max(n, 1)


def _fake_data(roast_id: str, now: datetime) -> dict:
    """
    生成一组基于 roastId 的确定性伪数据，供各类新模板使用。
    同一 roastId 每次调用返回同样的数据，保证幂等。
    """
    rid = roast_id or "anon"

    # 打卡数据卡（checkin）
    impact_score = 88 + _hash_ints(rid, "impact", 12)                    # 88 ~ 99
    clarity_bonus = 60 + _hash_ints(rid, "clarity", 40)                  # +60 ~ +99
    resonance = 3 + _hash_ints(rid, "resonance", 3)                      # 3 ~ 5 星
    streak_days = 1 + _hash_ints(rid, "streak", 21)                      # 连续 1 ~ 21 天

    # 处方笺（rx）
    rx_no = f"Rx-{now.strftime('%Y%m%d')}-{_hash_ints(rid, 'rx', 900) + 100:03d}"

    # 年度骂醒（wrapped）
    beat_pct = 60 + _hash_ints(rid, "beat", 40)                          # 击败 60% ~ 99%
    top_rank = 1 + _hash_ints(rid, "rank", 100)                          # 排名 #1 ~ #100

    # 黑胶评论（comment）
    like_count_base = 800 + _hash_ints(rid, "like", 90000)               # 800 ~ 90800
    like_count = f"{like_count_base / 10000:.1f}万" if like_count_base >= 10000 else str(like_count_base)
    reply_count = 20 + _hash_ints(rid, "reply", 300)                     # 20 ~ 320

    # 单曲（track）
    track_no = 1 + _hash_ints(rid, "track", 12)                          # Track 01 ~ 12
    track_dur_sec = 40 + _hash_ints(rid, "dur", 260)                     # 0:40 ~ 5:00
    track_dur = f"{track_dur_sec // 60}:{track_dur_sec % 60:02d}"

    # 塔罗（tarot）
    tarot_names = [
        ("XVII", "THE MIRROR", "镜面"),
        ("XIII", "THE AWAKENING", "苏醒"),
        ("VII",  "THE ROAST", "焚身"),
        ("IX",   "THE HERMIT", "隐者"),
        ("XVIII","THE MOON", "月相"),
        ("XX",   "THE JUDGEMENT", "审判"),
        ("XIV",  "TEMPERANCE", "自持"),
        ("XI",   "STRENGTH", "力量"),
    ]
    tarot_idx = _hash_ints(rid, "tarot", len(tarot_names))
    tarot_no, tarot_en, tarot_cn = tarot_names[tarot_idx]

    return {
        # 打卡
        "impactScore": impact_score,
        "clarityBonus": clarity_bonus,
        "resonanceStars": resonance,
        "streakDays": streak_days,
        # 处方
        "rxNo": rx_no,
        # 年度
        "beatPct": beat_pct,
        "topRank": top_rank,
        # 评论
        "likeCount": like_count,
        "replyCount": reply_count,
        # 单曲
        "trackNo": f"{track_no:02d}",
        "trackDuration": track_dur,
        # 塔罗
        "tarotNo": tarot_no,
        "tarotEn": tarot_en,
        "tarotCn": tarot_cn,
    }


# ---------- Jinja2 引擎 ----------
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


# ---------- DTO ----------
class GenerateCardDTO(BaseModel):
    roast_id: str = Field(alias="roastId")
    template: Optional[str] = "chat"

    model_config = {"populate_by_name": True}


class CardResultDTO(BaseModel):
    roast_id: str = Field(alias="roastId")
    template: str
    template_name: str = Field(alias="templateName")
    image_url: str = Field(alias="imageUrl")
    image_base64: str = Field(alias="imageBase64")
    width: int
    height: int
    size_bytes: int = Field(alias="sizeBytes")

    model_config = {"populate_by_name": True}


# ---------- Service ----------
def _sanitize_filename(name: str) -> str:
    """防路径穿越"""
    return re.sub(r"[^\w.\-]", "", name)


def generate_card(roast_id: str, template_key: str | None, openid: str | None = None) -> CardResultDTO:
    record = get_record(roast_id)
    tpl = get_card_template(template_key)

    # 1. Jinja2 渲染 HTML
    try:
        now = datetime.now()
        fake = _fake_data(roast_id, now)
        html = _jinja.get_template(tpl.template_name).render(
            content=record.content,
            contentLength=len(record.content),
            userInput=record.user_input,
            userInputLength=len(record.user_input),
            styleName=record.style.display_name,
            styleEmoji=record.style.emoji,
            styleKey=record.style.key,
            dateStr=now.strftime("%Y.%m.%d"),
            timeStr=now.strftime("%H:%M"),
            serialNo=_next_serial_no(roast_id),
            ganzhiYear=_ganzhi_year(now.year),
            qrcodeUrl=None,
            **fake,
        )
    except Exception as e:
        logger.exception("[CardService] 模板渲染失败, template=%s", tpl.key)
        raise BusinessException(ErrorCode.CARD_GENERATE_FAILED, "模板渲染失败") from e

    # 2. Playwright 截图
    try:
        png_bytes = pool.render_html_to_png(html, settings.card_width, settings.card_height)
    except Exception as e:
        logger.exception("[CardService] 截图失败")
        raise BusinessException(
            ErrorCode.CARD_GENERATE_FAILED, f"卡片渲染失败：{e}"
        ) from e

    # 3. 落盘（备用；主链路走 Base64）
    file_name = f"{roast_id}_{tpl.key}.png"
    try:
        os.makedirs(settings.card_output_dir, exist_ok=True)
        with open(Path(settings.card_output_dir) / file_name, "wb") as f:
            f.write(png_bytes)
    except Exception as e:
        logger.warning("[CardService] 卡片落盘失败（不影响返回）：%s", e)

    logger.info(
        "[CardService] 卡片生成成功: roastId=%s, template=%s, size=%dKB",
        roast_id, tpl.key, len(png_bytes) // 1024,
    )

    # 3.5 埋点：generate 事件（静默失败，不阻塞主链路）
    repo.log_card_event(
        template=tpl.key,
        event="generate",
        openid=openid or record.openid,
        roast_id=roast_id,
    )

    # 4. Base64 内嵌返回（云托管无需公网资源即可展示）
    b64 = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    return CardResultDTO(
        roast_id=roast_id,
        template=tpl.key,
        template_name=tpl.display_name,
        image_url=f"/api/card/image/{file_name}",
        image_base64=b64,
        width=settings.card_width,
        height=settings.card_height,
        size_bytes=len(png_bytes),
    )


def read_card_image(file_name: str) -> bytes:
    """读取卡片文件（GET 图片接口）"""
    safe = _sanitize_filename(file_name)
    if ".." in safe or "/" in safe or "\\" in safe:
        raise BusinessException(ErrorCode.PARAM_ERROR, "非法文件名")
    path = Path(settings.card_output_dir) / safe
    if not path.exists():
        raise BusinessException(ErrorCode.NOT_FOUND, "卡片不存在或已过期")
    return path.read_bytes()


# ---------- FastAPI Router ----------
router = APIRouter(prefix="/api/card", tags=["card"])


@router.post("", response_model=Result)
def api_generate(req: GenerateCardDTO, openid: str = Depends(get_openid)):
    return Result.success(
        generate_card(req.roast_id, req.template, openid=openid).model_dump(by_alias=True)
    )


@router.get("/image/{file_name}")
def api_get_image(file_name: str):
    data = read_card_image(file_name)
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/templates", response_model=Result)
def api_list_templates():
    templates = [
        {"key": t.key, "name": t.display_name}
        for t in CARD_TEMPLATES.values()
    ]
    return Result.success(templates)
