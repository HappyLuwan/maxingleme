package com.mxlm.card;

import com.mxlm.common.Result;
import com.mxlm.common.enums.CardTemplate;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

/**
 * 卡片生成接口
 */
@RestController
@RequestMapping("/api/card")
@RequiredArgsConstructor
public class CardController {

    private final CardService cardService;

    /**
     * 生成卡片
     * <p>
     * POST /api/card
     * body: { roastId, template }
     */
    @PostMapping
    public Result<CardService.CardResult> generate(@RequestBody GenerateCardDTO req) {
        return Result.success(cardService.generate(req.getRoastId(), req.getTemplate()));
    }

    /**
     * 获取卡片图片（浏览器 / 小程序可直接下载）
     * <p>
     * GET /api/card/image/{fileName}
     */
    @GetMapping("/image/{fileName}")
    public ResponseEntity<byte[]> getImage(@PathVariable String fileName) {
        byte[] data = cardService.readImage(fileName);
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .header(HttpHeaders.CACHE_CONTROL, "public, max-age=3600")
                .body(data);
    }

    /**
     * 获取所有可用卡片模板
     * <p>
     * GET /api/card/templates
     */
    @GetMapping("/templates")
    public Result<List<Map<String, Object>>> listTemplates() {
        List<Map<String, Object>> templates = Arrays.stream(CardTemplate.values())
                .map(t -> Map.<String, Object>of(
                        "key", t.getKey(),
                        "name", t.getDisplayName()
                ))
                .toList();
        return Result.success(templates);
    }

    @Data
    public static class GenerateCardDTO {
        @NotBlank
        private String roastId;
        /** 模板 key：attack / chat / poster，不传默认 chat */
        private String template;
    }
}
