package com.mxlm.ai;

import com.mxlm.ai.config.AIRuntimeConfig;
import com.mxlm.common.BusinessException;
import com.mxlm.common.ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * AI 路由器 / 调度器
 * <p>
 * 职责：
 * <ul>
 *   <li>根据当前 active provider 分发请求</li>
 *   <li>失败时自动尝试 fallback provider</li>
 *   <li>统计各 provider 调用情况</li>
 * </ul>
 * <p>
 * Spring 会自动把所有实现 {@link AIProvider} 的 Bean 注入到 providers Map 中，
 * key 为 @Component 注解上指定的 beanName（即 provider 的 key）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AIRouter {

    /** 所有 provider 实现，key = providerKey（如 "deepseek"）*/
    private final Map<String, AIProvider> providers;

    private final AIRuntimeConfig runtimeConfig;

    /**
     * 调用 AI 生成文本，自动 fallback。
     *
     * @param request 请求
     * @return AI 响应
     */
    public ChatResponse chat(ChatRequest request) {
        String activeKey = runtimeConfig.getActiveProvider();
        String fallbackKey = runtimeConfig.getFallbackProvider();

        // 1. 尝试默认 provider
        try {
            AIProvider provider = getProvider(activeKey);
            if (provider != null && provider.isAvailable()) {
                return provider.chat(request);
            }
            log.warn("[AIRouter] 默认 provider {} 不可用，尝试 fallback", activeKey);
        } catch (Exception e) {
            log.error("[AIRouter] 默认 provider {} 调用失败：{}", activeKey, e.getMessage());
        }

        // 2. 尝试 fallback provider
        if (fallbackKey != null && !fallbackKey.equals(activeKey)) {
            try {
                AIProvider fallback = getProvider(fallbackKey);
                if (fallback != null && fallback.isAvailable()) {
                    log.info("[AIRouter] 使用 fallback provider: {}", fallbackKey);
                    return fallback.chat(request);
                }
            } catch (Exception e) {
                log.error("[AIRouter] fallback provider {} 调用失败：{}", fallbackKey, e.getMessage());
            }
        }

        // 3. 都失败，抛异常
        throw new BusinessException(ErrorCode.AI_ALL_PROVIDERS_FAILED);
    }

    /**
     * 通过指定 provider key 调用（后台管理测试用）
     */
    public ChatResponse chatWith(String providerKey, ChatRequest request) {
        AIProvider provider = getProvider(providerKey);
        if (provider == null) {
            throw new BusinessException(ErrorCode.AI_PROVIDER_NOT_FOUND,
                    "Provider 不存在：" + providerKey);
        }
        if (!provider.isAvailable()) {
            throw new BusinessException(ErrorCode.AI_PROVIDER_NOT_FOUND,
                    "Provider 未启用或配置不完整：" + providerKey);
        }
        return provider.chat(request);
    }

    /**
     * 列出所有已注册的 provider
     */
    public List<AIProvider> listProviders() {
        return providers.values().stream().toList();
    }

    /**
     * 获取指定 provider
     */
    public AIProvider getProvider(String key) {
        if (key == null) {
            return null;
        }
        return providers.get(key);
    }
}
