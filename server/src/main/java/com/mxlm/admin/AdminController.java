package com.mxlm.admin;

import com.mxlm.ai.AIProvider;
import com.mxlm.ai.AIRouter;
import com.mxlm.ai.ChatRequest;
import com.mxlm.ai.ChatResponse;
import com.mxlm.ai.config.AIRuntimeConfig;
import com.mxlm.common.BusinessException;
import com.mxlm.common.ErrorCode;
import com.mxlm.common.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 后台管理接口 - AI 切换与测试
 * <p>
 * 简易鉴权：请求头 X-Admin-Token 必须与配置的 admin.token 一致。
 */
@Slf4j
@RestController
@RequestMapping("/admin/ai")
@RequiredArgsConstructor
public class AdminController {

    private final AIRouter aiRouter;
    private final AIRuntimeConfig runtimeConfig;

    @Value("${admin.token}")
    private String adminToken;

    /**
     * 列出所有 provider
     */
    @GetMapping("/providers")
    public Result<List<Map<String, Object>>> listProviders(HttpServletRequest req) {
        checkAuth(req);
        String active = runtimeConfig.getActiveProvider();
        String fallback = runtimeConfig.getFallbackProvider();

        List<Map<String, Object>> list = aiRouter.listProviders().stream()
                .map(p -> Map.<String, Object>of(
                        "key", p.getKey(),
                        "name", p.getName(),
                        "available", p.isAvailable(),
                        "isActive", p.getKey().equals(active),
                        "isFallback", p.getKey().equals(fallback)
                ))
                .toList();
        return Result.success(list);
    }

    /**
     * 切换 active provider
     */
    @PostMapping("/switch")
    public Result<Map<String, String>> switchProvider(HttpServletRequest req,
                                                      @RequestBody SwitchDTO dto) {
        checkAuth(req);
        AIProvider provider = aiRouter.getProvider(dto.getProviderKey());
        if (provider == null) {
            throw new BusinessException(ErrorCode.AI_PROVIDER_NOT_FOUND);
        }
        runtimeConfig.switchProvider(dto.getProviderKey());
        return Result.success(Map.of(
                "activeProvider", runtimeConfig.getActiveProvider(),
                "fallbackProvider", runtimeConfig.getFallbackProvider()
        ));
    }

    /**
     * 切换 fallback provider
     */
    @PostMapping("/switch-fallback")
    public Result<Map<String, String>> switchFallback(HttpServletRequest req,
                                                      @RequestBody SwitchDTO dto) {
        checkAuth(req);
        runtimeConfig.switchFallbackProvider(dto.getProviderKey());
        return Result.success(Map.of(
                "activeProvider", runtimeConfig.getActiveProvider(),
                "fallbackProvider", runtimeConfig.getFallbackProvider()
        ));
    }

    /**
     * 测试指定 provider（不受 active 影响，直连指定 provider）
     */
    @PostMapping("/test")
    public Result<ChatResponse> test(HttpServletRequest req, @RequestBody TestDTO dto) {
        checkAuth(req);
        ChatRequest chatReq = ChatRequest.builder()
                .systemPrompt(dto.getSystemPrompt() != null ? dto.getSystemPrompt() :
                        "你是一个测试用的 AI 助手，请用一句话回复。")
                .userInput(dto.getUserInput() != null ? dto.getUserInput() : "Hello")
                .build();
        return Result.success(aiRouter.chatWith(dto.getProviderKey(), chatReq));
    }

    private void checkAuth(HttpServletRequest req) {
        String token = req.getHeader("X-Admin-Token");
        if (token == null || !token.equals(adminToken)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "后台鉴权失败");
        }
    }

    @lombok.Data
    public static class SwitchDTO {
        private String providerKey;
    }

    @lombok.Data
    public static class TestDTO {
        private String providerKey;
        private String systemPrompt;
        private String userInput;
    }
}
