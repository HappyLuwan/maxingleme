"""
Playwright 无头浏览器单例池
对应 Java 的 PlaywrightPool

关键设计：
- 用 sync_playwright() 单例保持 Browser 常驻，避免每次截图重启浏览器
- 首次启动会自动检测 Chromium，若未安装可通过环境变量 PLAYWRIGHT_BROWSERS_PATH 指定路径
- 线程安全：使用 asyncio.Lock（若需异步）或 threading.Lock（同步版）
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from playwright.sync_api import Browser, Playwright, sync_playwright

from app.config import settings

logger = logging.getLogger(__name__)


class PlaywrightPool:
    """浏览器单例池"""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = threading.Lock()
        self._enabled = settings.card_playwright_enabled

    def start(self) -> None:
        """启动 Playwright（应用启动时调用）"""
        if not self._enabled:
            logger.warning("[PlaywrightPool] Playwright 已禁用，卡片功能不可用")
            return
        try:
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
        except Exception as e:
            logger.exception("[PlaywrightPool] 初始化失败：%s", e)
            logger.error(
                "首次运行请执行: playwright install chromium"
            )

    def stop(self) -> None:
        """关闭浏览器（应用停机时调用）"""
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

    def render_html_to_png(self, html: str, width: int, height: int) -> bytes:
        """
        将 HTML 渲染为 PNG 字节数组
        每次创建独立 BrowserContext 保证隔离，但线程要加锁串行访问 browser
        """
        if self._browser is None:
            raise RuntimeError("Playwright 未初始化")
        with self._lock:
            context = self._browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2.0,  # 2 倍图更清晰
            )
            try:
                page = context.new_page()
                page.set_content(html, wait_until="networkidle")
                page.wait_for_timeout(200)  # 等字体渲染稳定
                return page.screenshot(type="png", full_page=False, omit_background=False)
            finally:
                context.close()


pool = PlaywrightPool()
