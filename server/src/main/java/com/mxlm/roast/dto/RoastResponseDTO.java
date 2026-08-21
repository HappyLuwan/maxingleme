package com.mxlm.roast.dto;

import lombok.Builder;
import lombok.Data;

/**
 * 骂醒响应 DTO
 */
@Data
@Builder
public class RoastResponseDTO {

    /** 骂醒记录唯一 ID（用于后续生成卡片） */
    private String roastId;

    /** AI 生成的骂醒文案 */
    private String content;

    /** 使用的风格 key */
    private String style;

    /** 风格显示名，如"东北大姐" */
    private String styleName;

    /** 风格 emoji */
    private String styleEmoji;

    /** 使用的 AI provider（用于展示 or 埋点） */
    private String provider;

    /** 耗时（毫秒） */
    private Long costMillis;
}
