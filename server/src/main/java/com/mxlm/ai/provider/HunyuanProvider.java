package com.mxlm.ai.provider;

import com.mxlm.ai.config.AIProperties;
import org.springframework.stereotype.Component;

/**
 * 腾讯混元 AI Provider（OpenAI 兼容接口）
 * <p>
 * 文档：https://cloud.tencent.com/document/product/1729
 */
@Component("hunyuan")
public class HunyuanProvider extends AbstractOpenAICompatibleProvider {

    public HunyuanProvider(AIProperties aiProperties) {
        super(aiProperties.getProviders().get("hunyuan"), aiProperties.getTimeout());
    }

    @Override
    public String getKey() {
        return "hunyuan";
    }

    @Override
    public String getName() {
        return "腾讯混元";
    }
}
