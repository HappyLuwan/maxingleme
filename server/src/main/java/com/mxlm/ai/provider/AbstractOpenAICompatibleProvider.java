package com.mxlm.ai.provider;

import cn.hutool.core.util.StrUtil;
import com.mxlm.ai.AIProvider;
import com.mxlm.ai.ChatRequest;
import com.mxlm.ai.ChatResponse;
import com.mxlm.ai.config.AIProperties;
import com.mxlm.common.BusinessException;
import com.mxlm.common.ErrorCode;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.ChatMessage;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.model.output.Response;
import dev.langchain4j.model.output.TokenUsage;
import lombok.extern.slf4j.Slf4j;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * OpenAI 协议兼容 Provider 抽象基类（基于 LangChain4j 重写）
 * <p>
 * DeepSeek、混元、豆包、通义千问、Kimi 等主流国产大模型均提供 OpenAI 兼容接口，
 * LangChain4j 的 OpenAiChatModel 通过自定义 baseUrl 即可直连。
 * <p>
 * 相比原来手写 WebClient：
 * <ul>
 *   <li>统一的 ChatLanguageModel 抽象，切换模型只改一行配置</li>
 *   <li>内置重试、超时、Token 计数</li>
 *   <li>未来可无缝集成 memory、tools、RAG</li>
 * </ul>
 */
@Slf4j
public abstract class AbstractOpenAICompatibleProvider implements AIProvider {

    protected final AIProperties.ProviderConfig config;
    protected final Integer timeoutMs;

    /** 懒加载的 LangChain4j 模型 */
    protected volatile ChatLanguageModel chatModel;

    protected AbstractOpenAICompatibleProvider(AIProperties.ProviderConfig config, Integer timeoutMs) {
        this.config = config;
        this.timeoutMs = timeoutMs != null ? timeoutMs : 30000;
    }

    @Override
    public boolean isAvailable() {
        return config != null
                && Boolean.TRUE.equals(config.getEnabled())
                && StrUtil.isNotBlank(config.getApiKey())
                && !config.getApiKey().startsWith("sk-your-")
                && !config.getApiKey().startsWith("your-")
                && StrUtil.isNotBlank(config.getApiUrl())
                && StrUtil.isNotBlank(config.getModel());
    }

    /** 懒加载获取模型 */
    protected ChatLanguageModel getChatModel() {
        if (chatModel == null) {
            synchronized (this) {
                if (chatModel == null) {
                    chatModel = buildChatModel();
                }
            }
        }
        return chatModel;
    }

    /** 子类可覆盖以自定义构建逻辑（默认 OpenAI 兼容） */
    protected ChatLanguageModel buildChatModel() {
        String baseUrl = normalizeBaseUrl(config.getApiUrl());
        return OpenAiChatModel.builder()
                .baseUrl(baseUrl)
                .apiKey(config.getApiKey())
                .modelName(config.getModel())
                .temperature(config.getTemperature())
                .maxTokens(config.getMaxTokens())
                .timeout(Duration.ofMillis(timeoutMs))
                .logRequests(false)
                .logResponses(false)
                .build();
    }

    /**
     * baseUrl 归一化：兼容"完整 URL"和"根域名"两种配置写法
     * - https://api.deepseek.com/v1/chat/completions -> https://api.deepseek.com/v1
     * - https://api.deepseek.com/v1                   -> https://api.deepseek.com/v1
     */
    protected String normalizeBaseUrl(String apiUrl) {
        if (StrUtil.isBlank(apiUrl)) return apiUrl;
        String url = apiUrl.trim();
        if (url.endsWith("/chat/completions")) {
            url = url.substring(0, url.length() - "/chat/completions".length());
        }
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }

    @Override
    public ChatResponse chat(ChatRequest request) {
        long start = System.currentTimeMillis();
        if (!isAvailable()) {
            throw new BusinessException(ErrorCode.AI_PROVIDER_NOT_FOUND,
                    getKey() + " 未启用或配置不完整");
        }

        // 组装 LangChain4j 消息列表
        List<ChatMessage> messages = new ArrayList<>();
        if (StrUtil.isNotBlank(request.getSystemPrompt())) {
            messages.add(SystemMessage.from(request.getSystemPrompt()));
        }
        messages.add(UserMessage.from(request.getUserInput()));

        // 请求级参数覆盖时构建临时模型，否则复用共享模型
        ChatLanguageModel model = needsPerRequestModel(request)
                ? buildPerRequestModel(request)
                : getChatModel();

        try {
            Response<AiMessage> response = model.generate(messages);
            AiMessage aiMessage = response.content();
            String content = aiMessage != null ? aiMessage.text() : null;
            TokenUsage usage = response.tokenUsage();

            return ChatResponse.builder()
                    .content(content != null ? content.trim() : "")
                    .model(config.getModel())
                    .provider(getKey())
                    .promptTokens(usage != null ? usage.inputTokenCount() : null)
                    .completionTokens(usage != null ? usage.outputTokenCount() : null)
                    .totalTokens(usage != null ? usage.totalTokenCount() : null)
                    .costMillis(System.currentTimeMillis() - start)
                    .build();
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("[{}] LangChain4j 调用异常", getKey(), e);
            throw new BusinessException(ErrorCode.AI_CALL_FAILED,
                    getKey() + " 调用失败：" + e.getMessage());
        }
    }

    private boolean needsPerRequestModel(ChatRequest request) {
        boolean overrideTemp = request.getTemperature() != null
                && !request.getTemperature().equals(config.getTemperature());
        boolean overrideTokens = request.getMaxTokens() != null
                && !request.getMaxTokens().equals(config.getMaxTokens());
        return overrideTemp || overrideTokens;
    }

    private ChatLanguageModel buildPerRequestModel(ChatRequest request) {
        return OpenAiChatModel.builder()
                .baseUrl(normalizeBaseUrl(config.getApiUrl()))
                .apiKey(config.getApiKey())
                .modelName(config.getModel())
                .temperature(request.getTemperature() != null
                        ? request.getTemperature() : config.getTemperature())
                .maxTokens(request.getMaxTokens() != null
                        ? request.getMaxTokens() : config.getMaxTokens())
                .timeout(Duration.ofMillis(timeoutMs))
                .build();
    }
}

