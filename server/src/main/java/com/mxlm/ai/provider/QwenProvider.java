package com.mxlm.ai.provider;

import com.mxlm.ai.config.AIProperties;
import org.springframework.stereotype.Component;

/**
 * 阿里通义千问 AI Provider（DashScope OpenAI 兼容接口）
 * <p>
 * 文档：https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope
 */
@Component("qwen")
public class QwenProvider extends AbstractOpenAICompatibleProvider {

    public QwenProvider(AIProperties aiProperties) {
        super(aiProperties.getProviders().get("qwen"), aiProperties.getTimeout());
    }

    @Override
    public String getKey() {
        return "qwen";
    }

    @Override
    public String getName() {
        return "通义千问";
    }
}
