"""
Playwright 无头浏览器单例池
对应 Java 的 PlaywrightPool

关键设计：
- FastAPI 运行在 asyncio 事件循环里，sync_playwright() 无法直接在该循环里 start
- 解决方案：把 Playwright 的所有同步调用都派发到一个独立的专用线程里执行
  该线程没有 asyncio 事件循环，因此 sync_playwright 可以正常工作
- 用队列 (concurrent.futures) 让外部（异步/同步）都能安全地调用截图
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional

from playwright.sync_api import Browser, Playwright, sync_playwright

from app.config import settings

logger = logging.getLogger(__name__)


class PlaywrightPool:
    """浏览器单例池（所有 Playwright 操作都在专用单线程内执行）"""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._render_lock = threading.Lock()
        self._enabled = settings.card_playwright_enabled
        # 关键：单线程 Executor —— 保证所有 Playwright 调用都在同一个非 asyncio 线程里
        self._executor: Optional[ThreadPoolExecutor] = None
        self._started = False

    # ---------- 内部：真正在专用线程里执行的方法 ----------
    def _do_start(self) -> None:
        logger.info("[PlaywrightPool] 初始化 Playwright...")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        logger.info("[PlaywrightPool] Playwright 初始化成功")

    def _do_stop(self) -> None:
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            logger.info("[PlaywrightPool] 已关闭")
        except Exception as e:
            logger.warning("[PlaywrightPool] 关闭异常：%s", e)

    def _do_render(self, html: str, width: int, height: int) -> bytes:
        if self._browser is None:
            raise RuntimeError("Playwright 未初始化")
        context = self._browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=2.0,
        )
        try:
            page = context.new_page()
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(200)
            return page.screenshot(type="png", full_page=False, omit_background=False)
        finally:
            context.close()

    # ---------- 对外：把调用派发到专用线程 ----------
    def start(self) -> None:
        """启动 Playwright（应用启动时调用）—— 惰性初始化，失败不影响服务启动"""
        if not self._enabled:
            logger.warning("[PlaywrightPool] Playwright 已禁用，卡片功能不可用")
            return
        if self._started:
            return
        try:
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="playwright-worker",
            )
            fut: Future = self._executor.submit(self._do_start)
            fut.result(timeout=60)  # 等待启动完成，超时抛异常
            self._started = True
        except Exception as e:
            logger.exception("[PlaywrightPool] 初始化失败：%s", e)
            logger.error("首次运行请执行: playwright install chromium")
            # 保证探针能通：不抛出，卡片功能降级
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None

    def stop(self) -> None:
        """关闭浏览器（应用停机时调用）"""
        if self._executor is None:
            return
        try:
            fut = self._executor.submit(self._do_stop)
            fut.result(timeout=15)
        except Exception as e:
            logger.warning("[PlaywrightPool] 关闭异常：%s", e)
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
            self._started = False

    def render_html_to_png(self, html: str, width: int, height: int) -> bytes:
        """将 HTML 渲染为 PNG 字节数组（线程安全，串行执行）"""
        if not self._started or self._executor is None:
            raise RuntimeError(
                "Playwright 未初始化成功，卡片功能不可用；请检查容器内是否安装了 chromium"
            )
        # 加锁保证同一时刻只有一个截图任务在专用线程里跑
        with self._render_lock:
            fut: Future = self._executor.submit(self._do_render, html, width, height)
            return fut.result(timeout=60)


pool = PlaywrightPool()
