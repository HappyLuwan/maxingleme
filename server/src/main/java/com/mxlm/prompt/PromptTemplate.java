package com.mxlm.prompt;

import com.mxlm.common.enums.RoastStyle;

/**
 * Prompt 模板接口
 * <p>
 * 每种骂醒风格对应一个 PromptTemplate 实现。通过 Spring 注入 + Map 分发。
 */
public interface PromptTemplate {

    /**
     * 对应的风格
     */
    RoastStyle getStyle();

    /**
     * 生成 system prompt（人格设定）
     */
    String buildSystemPrompt();

    /**
     * 建议的温度值（不同风格温度不同，让效果更贴合）
     */
    default Double getTemperature() {
        return 1.1;
    }

    /**
     * 建议的最大 token 数
     */
    default Integer getMaxTokens() {
        return 300;
    }
}
