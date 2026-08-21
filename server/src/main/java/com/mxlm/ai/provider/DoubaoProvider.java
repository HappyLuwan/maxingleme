package com.mxlm.ai.provider;

import com.mxlm.ai.config.AIProperties;
import org.springframework.stereotype.Component;

/**
 * 字节豆包 AI Provider（火山方舟）
 * <p>
 * 文档：https://www.volcengine.com/docs/82379
 */
@Component("doubao")
public class DoubaoProvider extends AbstractOpenAICompatibleProvider {

    public DoubaoProvider(AIProperties aiProperties) {
        super(aiProperties.getProviders().get("doubao"), aiProperties.getTimeout());
    }

    @Override
    public String getKey() {
        return "doubao";
    }

    @Override
    public String getName() {
        return "字节豆包";
    }
}
