package com.mxlm.prompt;

import com.mxlm.common.enums.RoastStyle;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Prompt 注册中心
 * <p>
 * 启动时自动收集所有 {@link PromptTemplate} 实现，按 RoastStyle 分类。
 * 业务代码通过 {@link #get(RoastStyle)} 获取对应风格的 Prompt。
 */
@Slf4j
@Component
public class PromptRegistry {

    private final Map<RoastStyle, PromptTemplate> registry = new EnumMap<>(RoastStyle.class);
    private final List<PromptTemplate> templates;

    public PromptRegistry(List<PromptTemplate> templates) {
        this.templates = templates;
    }

    @PostConstruct
    public void init() {
        for (PromptTemplate template : templates) {
            registry.put(template.getStyle(), template);
        }
        log.info("[PromptRegistry] 已注册 {} 种风格 Prompt: {}", registry.size(), registry.keySet());
    }

    /**
     * 获取指定风格的 Prompt 模板，找不到返回 DUSHE（默认）
     */
    public PromptTemplate get(RoastStyle style) {
        PromptTemplate template = registry.get(style);
        if (template == null) {
            log.warn("[PromptRegistry] 未找到风格 {} 的 Prompt，使用默认 DUSHE", style);
            return registry.get(RoastStyle.DUSHE);
        }
        return template;
    }
}
