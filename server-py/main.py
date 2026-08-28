"""
FastAPI 应用入口
对应 Java 的 MaXingLeMeApplication
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

# ---------- 尽早加载 .env（供 db.py 等裸 os.getenv 使用）----------
# 云托管环境直接注入环境变量，.env 不存在也无副作用
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # 已存在的系统环境变量优先（云托管注入的不会被覆盖）
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin import admin_data_router, router as admin_router
from app.analytics import admin_router as analytics_admin_router, api_router as analytics_api_router
from app.card import router as card_router
from app.common import (
    BusinessException,
    Result,
    business_exception_handler,
    unhandled_exception_handler,
)
from app.config import settings
from app.db import close_db, db_path, init_db
from app.history import router as history_router
from app.playwright_pool import pool
from app.roast import router as roast_router
from app import cleanup

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
    # 数据库初始化（建表/迁移）—— 同步执行，失败即快速失败
    init_db()
    logger.info("[DB] SQLite 路径: %s", db_path())
    # 定时清理任务
    cleanup.start()
    # Playwright 初始化异步执行，避免阻塞 asyncio 事件循环 & 探针
    # 即使 Playwright 初始化失败也不影响主服务启动（卡片功能降级）
    import asyncio
    asyncio.get_event_loop().run_in_executor(None, pool.start)
    yield
    logger.info("===== 骂醒了么 · 服务关闭 =====")
    cleanup.stop()
    pool.stop()
    close_db()


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
app.include_router(history_router)
app.include_router(analytics_api_router)
app.include_router(admin_router)
app.include_router(admin_data_router)
app.include_router(analytics_admin_router)

# ---------- 静态资源（admin 后台 UI） ----------
from pathlib import Path as _Path
# main.py 位于 server-py/ 根目录，静态资源在 app/static
_static_dir = _Path(__file__).parent / "app" / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/admin.html", tags=["system"], include_in_schema=False)
def admin_page():
    """Admin 后台单页 UI"""
    from fastapi.responses import FileResponse
    idx = _static_dir / "admin.html"
    if not idx.exists():
        return {"error": "admin.html not found", "expected": str(idx)}
    return FileResponse(str(idx), media_type="text/html")


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
