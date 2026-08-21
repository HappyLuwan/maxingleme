package com.mxlm.card;

import com.mxlm.common.BusinessException;
import com.mxlm.common.ErrorCode;
import com.mxlm.common.enums.CardTemplate;
import com.mxlm.common.enums.RoastStyle;
import com.mxlm.roast.RoastRecord;
import com.mxlm.roast.RoastService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Base64;

/**
 * 卡片生成服务
 * <p>
 * 流程：读取 RoastRecord → Thymeleaf 渲染 HTML → Playwright 截图为 PNG → 保存到本地/云存储 → 返回 URL
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CardService {

    private final RoastService roastService;
    private final TemplateEngine templateEngine;
    private final PlaywrightPool playwrightPool;

    @Value("${card.output-dir:/tmp/mxlm-cards}")
    private String outputDir;

    @Value("${card.width:750}")
    private int cardWidth;

    @Value("${card.height:1000}")
    private int cardHeight;

    @Value("${server.port:8080}")
    private String serverPort;

    /**
     * 生成卡片
     *
     * @param roastId  骂醒记录 ID
     * @param template 卡片模板 key
     * @return 生成的卡片文件相对路径（可通过 GET /api/card/image/{id} 访问）
     */
    public CardResult generate(String roastId, String template) {
        RoastRecord record = roastService.getById(roastId);
        CardTemplate cardTemplate = CardTemplate.fromKey(template);

        // 1. 构造 Thymeleaf 上下文
        Context ctx = new Context();
        String content = record.getContent();
        String userInput = record.getUserInput();
        RoastStyle style = record.getStyle();

        ctx.setVariable("content", content);
        ctx.setVariable("contentLength", content.length());
        ctx.setVariable("userInput", userInput);
        ctx.setVariable("userInputLength", userInput.length());
        ctx.setVariable("styleName", style.getDisplayName());
        ctx.setVariable("styleEmoji", style.getEmoji());
        ctx.setVariable("dateStr", LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy.MM.dd")));
        // 二维码 URL：预留字段，未来接入云开发时替换（TODO: 生成小程序码接口）
        ctx.setVariable("qrcodeUrl", null);

        // 2. Thymeleaf 渲染 HTML
        String html;
        try {
            html = templateEngine.process(cardTemplate.getTemplateName(), ctx);
        } catch (Exception e) {
            log.error("[CardService] 模板渲染失败, template={}", cardTemplate, e);
            throw new BusinessException(ErrorCode.CARD_GENERATE_FAILED, "模板渲染失败");
        }

        // 3. Playwright 截图
        byte[] pngBytes;
        try {
            pngBytes = playwrightPool.renderHtmlToPng(html, cardWidth, cardHeight);
        } catch (Exception e) {
            log.error("[CardService] 卡片截图失败", e);
            throw new BusinessException(ErrorCode.CARD_GENERATE_FAILED, "卡片渲染失败：" + e.getMessage());
        }

        // 4. 保存文件（MVP：本地磁盘；V2：上传云存储）
        String fileName = roastId + "_" + cardTemplate.getKey() + ".png";
        Path outputPath = Paths.get(outputDir, fileName);
        try {
            Files.createDirectories(outputPath.getParent());
            Files.write(outputPath, pngBytes);
        } catch (IOException e) {
            log.error("[CardService] 卡片保存失败, path={}", outputPath, e);
            throw new BusinessException(ErrorCode.CARD_GENERATE_FAILED, "卡片保存失败");
        }

        log.info("[CardService] 卡片生成成功: roastId={}, template={}, size={}KB",
                roastId, cardTemplate.getKey(), pngBytes.length / 1024);

        // 5. Base64 内嵌返回（云托管零配置即可显示，前端 dataURL 直接用）
        String base64 = "data:image/png;base64," + Base64.getEncoder().encodeToString(pngBytes);

        return CardResult.builder()
                .roastId(roastId)
                .template(cardTemplate.getKey())
                .templateName(cardTemplate.getDisplayName())
                .imageUrl("/api/card/image/" + fileName)
                .imageBase64(base64)
                .width(cardWidth)
                .height(cardHeight)
                .sizeBytes(pngBytes.length)
                .build();
    }

    /**
     * 读取卡片文件
     */
    public byte[] readImage(String fileName) {
        // 安全：拒绝路径穿越
        if (fileName.contains("..") || fileName.contains("/") || fileName.contains("\\")) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "非法文件名");
        }
        Path path = Paths.get(outputDir, fileName);
        if (!Files.exists(path)) {
            throw new BusinessException(ErrorCode.NOT_FOUND, "卡片不存在或已过期");
        }
        try {
            return Files.readAllBytes(path);
        } catch (IOException e) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "读取卡片失败");
        }
    }

    /**
     * 卡片生成结果
     */
    @lombok.Builder
    @lombok.Data
    public static class CardResult {
        private String roastId;
        private String template;
        private String templateName;
        /** 备用：走公网访问域名时可用；云托管默认走 imageBase64 */
        private String imageUrl;
        /** 完整 dataURL（含 data:image/png;base64, 前缀），前端可直接放到 image src */
        private String imageBase64;
        private Integer width;
        private Integer height;
        private Integer sizeBytes;
    }
}
