package com.mxlm.card;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.LoadState;
import com.microsoft.playwright.options.ScreenshotType;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Playwright 浏览器池（单例）
 * <p>
 * Playwright 启动成本高（首次要下载 Chromium），故用单例保持一个 Browser 实例。
 * 每次截图创建独立 BrowserContext，保证隔离。
 * <p>
 * 若首次运行未安装浏览器，会自动执行 `playwright install chromium`。
 */
@Slf4j
@Component
public class PlaywrightPool {

    @Value("${card.playwright-enabled:true}")
    private boolean enabled;

    private Playwright playwright;
    private Browser browser;

    @PostConstruct
    public void init() {
        if (!enabled) {
            log.warn("[PlaywrightPool] Playwright 已禁用，卡片生成功能不可用");
            return;
        }
        try {
            log.info("[PlaywrightPool] 初始化 Playwright...");
            playwright = Playwright.create();
            browser = tryLaunchChromium();
            log.info("[PlaywrightPool] Playwright 初始化成功");
        } catch (Exception e) {
            // 首次运行 / 构建期未预下载：尝试运行时自动下载 Chromium
            log.warn("[PlaywrightPool] 首次启动检测到 Chromium 未安装，尝试自动下载... ({})", e.getMessage());
            try {
                // Playwright Java CLI 会下载 Chromium 到 PLAYWRIGHT_BROWSERS_PATH（默认 ~/.cache/ms-playwright）
                com.microsoft.playwright.CLI.main(new String[]{"install", "chromium"});
                log.info("[PlaywrightPool] Chromium 自动下载完成，重新初始化...");
                if (playwright == null) {
                    playwright = Playwright.create();
                }
                browser = tryLaunchChromium();
                log.info("[PlaywrightPool] Playwright 初始化成功（运行时下载模式）");
            } catch (Throwable retryEx) {
                log.error("[PlaywrightPool] Playwright 初始化失败，卡片生成将不可用。" +
                        "请检查网络或手动执行: mvn exec:java -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args=\"install chromium\"", retryEx);
            }
        }
    }

    /**
     * 启动 Chromium 浏览器
     */
    private Browser tryLaunchChromium() {
        return playwright.chromium().launch(new BrowserType.LaunchOptions()
                .setHeadless(true)
                .setArgs(java.util.List.of(
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                )));
    }

    /**
     * 将 HTML 渲染成 PNG 字节数组
     *
     * @param html   完整 HTML 内容
     * @param width  视口宽度
     * @param height 视口高度
     * @return PNG 字节数据
     */
    public byte[] renderHtmlToPng(String html, int width, int height) {
        if (browser == null) {
            throw new IllegalStateException("Playwright 未初始化");
        }
        try (BrowserContext context = browser.newContext(new Browser.NewContextOptions()
                .setViewportSize(width, height)
                .setDeviceScaleFactor(2.0)); // 2 倍图更清晰
             Page page = context.newPage()) {

            page.setContent(html);
            // 等 fonts + 图片加载完成
            page.waitForLoadState(LoadState.NETWORKIDLE);
            // 额外等 200ms 确保字体渲染稳定
            page.waitForTimeout(200);

            return page.screenshot(new Page.ScreenshotOptions()
                    .setType(ScreenshotType.PNG)
                    .setFullPage(false)
                    .setOmitBackground(false));
        }
    }

    @PreDestroy
    public void destroy() {
        try {
            if (browser != null) {
                browser.close();
            }
            if (playwright != null) {
                playwright.close();
            }
            log.info("[PlaywrightPool] 已关闭");
        } catch (Exception e) {
            log.warn("[PlaywrightPool] 关闭异常", e);
        }
    }
}
