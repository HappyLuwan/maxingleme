package com.mxlm.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI 聊天响应
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatResponse {

    /** 生成的文本内容 */
    private String content;

    /** 使用的模型名（如 deepseek-chat） */
    private String model;

    /** 使用的 provider（如 deepseek） */
    private String provider;

    /** 输入 token 数 */
    private Integer promptTokens;

    /** 输出 token 数 */
    private Integer completionTokens;

    /** 总 token 数 */
    private Integer totalTokens;

    /** 耗时（毫秒） */
    private Long costMillis;
}
