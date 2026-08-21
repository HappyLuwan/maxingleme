package com.mxlm.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI 聊天请求
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatRequest {

    /** 系统提示词（人格设定） */
    private String systemPrompt;

    /** 用户输入 */
    private String userInput;

    /** 温度：0.0-2.0，越高越随机；不传使用 provider 默认 */
    private Double temperature;

    /** 最大 token 数；不传使用 provider 默认 */
    private Integer maxTokens;
}
