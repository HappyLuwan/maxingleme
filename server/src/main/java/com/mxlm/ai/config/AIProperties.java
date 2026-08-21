package com.mxlm.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

/**
 * AI 配置类，映射 application.yml 中 ai.* 配置
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "ai")
public class AIProperties {

    /** 默认启用的 provider */
    private String defaultProvider = "deepseek";

    /** 兜底 provider（当默认失败时） */
    private String fallbackProvider = "hunyuan";

    /** 请求超时（毫秒） */
    private Integer timeout = 30000;

    /** 是否 mock 模式（本地开发不真实调用） */
    private Boolean mockMode = false;

    /** 各 provider 配置 */
    private Map<String, ProviderConfig> providers = new HashMap<>();

    /**
     * 单个 provider 的配置
     */
    @Data
    public static class ProviderConfig {
        /** 是否启用 */
        private Boolean enabled = false;
        /** API 地址 */
        private String apiUrl;
        /** API Key */
        private String apiKey;
        /** 模型名 */
        private String model;
        /** 温度 */
        private Double temperature = 1.0;
        /** 最大 token 数 */
        private Integer maxTokens = 500;
    }
}
