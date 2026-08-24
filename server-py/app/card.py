"""
卡片生成服务 + FastAPI 路由
对应 Java 的 CardService + CardController
"""
from __future__ import annotations

import base64
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field

from app.common import BusinessException, ErrorCode, Result
from app.config import settings
from app.enums import CARD_TEMPLATES, get_card_template
from app.playwright_pool import pool
from app.roast import get_record

logger = logging.getLogger(__name__)


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


def generate_card(roast_id: str, template_key: str | None) -> CardResultDTO:
    record = get_record(roast_id)
    tpl = get_card_template(template_key)

    # 1. Jinja2 渲染 HTML
    try:
        html = _jinja.get_template(tpl.template_name).render(
            content=record.content,
            contentLength=len(record.content),
            userInput=record.user_input,
            userInputLength=len(record.user_input),
            styleName=record.style.display_name,
            styleEmoji=record.style.emoji,
            dateStr=datetime.now().strftime("%Y.%m.%d"),
            qrcodeUrl=None,
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
def api_generate(req: GenerateCardDTO):
    return Result.success(generate_card(req.roast_id, req.template).model_dump(by_alias=True))


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
