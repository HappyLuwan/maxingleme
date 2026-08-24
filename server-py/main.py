"""
FastAPI 应用入口
对应 Java 的 MaXingLeMeApplication
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import router as admin_router
from app.card import router as card_router
from app.common import (
    BusinessException,
    Result,
    business_exception_handler,
    unhandled_exception_handler,
)
from app.config import settings
from app.playwright_pool import pool
from app.roast import router as roast_router

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    logger.info("===== 骂醒了么 · Python 版启动 =====")
    logger.info("active=%s, fallback=%s", settings.ai_active_provider, settings.ai_fallback_provider)
    # Playwright 初始化异步执行，避免阻塞 asyncio 事件循环 & 探针
    # 即使 Playwright 初始化失败也不影响主服务启动（卡片功能降级）
    import asyncio
    asyncio.get_event_loop().run_in_executor(None, pool.start)
    yield
    logger.info("===== 骂醒了么 · 服务关闭 =====")
    pool.stop()


app = FastAPI(
    title="骂醒了么 · 后端",
    description="AI 骂醒你，一键让你清醒",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 全局异常 ----------
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ---------- 路由 ----------
app.include_router(roast_router)
app.include_router(card_router)
app.include_router(admin_router)


# ---------- 健康检查 ----------
@app.get("/actuator/health", tags=["system"])
def health():
    return {"status": "UP"}


@app.get("/", tags=["system"])
def index():
    return Result.success({
        "service": "骂醒了么 · 后端",
        "version": "1.0.0",
        "docs": "/docs",
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_config=None,
    )
