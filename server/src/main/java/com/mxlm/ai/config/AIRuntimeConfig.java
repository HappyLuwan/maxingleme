package com.mxlm.ai.config;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicReference;

/**
 * AI Provider 运行时配置管理器
 * <p>
 * 用于管理"当前启用的 Provider"，支持运行时动态切换（通过后台接口）。
 * <p>
 * 设计：
 * <ul>
 *   <li>启动时从 {@link AIProperties} 读取默认 provider</li>
 *   <li>运行时后台管理接口可修改 activeProvider（无需重启）</li>
 *   <li>后续可扩展为从 DB 读取，配合缓存刷新机制</li>
 * </ul>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AIRuntimeConfig {

    private final AIProperties aiProperties;

    /** 当前启用的 provider（原子引用，保证线程安全） */
    private final AtomicReference<String> activeProvider = new AtomicReference<>();

    /** 兜底 provider */
    private final AtomicReference<String> fallbackProvider = new AtomicReference<>();

    @PostConstruct
    public void init() {
        activeProvider.set(aiProperties.getDefaultProvider());
        fallbackProvider.set(aiProperties.getFallbackProvider());
        log.info("[AIRuntimeConfig] 初始化完成，active={}, fallback={}",
                activeProvider.get(), fallbackProvider.get());
    }

    /**
     * 获取当前启用的 provider key
     */
    public String getActiveProvider() {
        return activeProvider.get();
    }

    /**
     * 切换启用的 provider（后台管理接口调用）
     *
     * @param providerKey 新的 provider key
     */
    public void switchProvider(String providerKey) {
        String old = activeProvider.getAndSet(providerKey);
        log.info("[AIRuntimeConfig] 切换 provider: {} -> {}", old, providerKey);
    }

    /**
     * 获取兜底 provider
     */
    public String getFallbackProvider() {
        return fallbackProvider.get();
    }

    /**
     * 切换兜底 provider
     */
    public void switchFallbackProvider(String providerKey) {
        String old = fallbackProvider.getAndSet(providerKey);
        log.info("[AIRuntimeConfig] 切换 fallback provider: {} -> {}", old, providerKey);
    }
}
