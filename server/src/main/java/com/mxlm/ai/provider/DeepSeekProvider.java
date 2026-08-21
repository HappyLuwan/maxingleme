package com.mxlm.ai.provider;

import com.mxlm.ai.config.AIProperties;
import org.springframework.stereotype.Component;

/**
 * DeepSeek AI Provider
 * <p>
 * 文档：https://api-docs.deepseek.com/
 * 价格：极其便宜（约 0.001 元/次）
 */
@Component("deepseek")
public class DeepSeekProvider extends AbstractOpenAICompatibleProvider {

    public DeepSeekProvider(AIProperties aiProperties) {
        super(aiProperties.getProviders().get("deepseek"), aiProperties.getTimeout());
    }

    @Override
    public String getKey() {
        return "deepseek";
    }

    @Override
    public String getName() {
        return "DeepSeek Chat";
    }
}
