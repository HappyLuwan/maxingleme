package com.mxlm.roast;

import com.mxlm.common.enums.RoastStyle;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 骂醒记录（内存版）
 * <p>
 * MVP 阶段先用内存 Map 缓存，验证需求后再持久化到数据库。
 * TTL 建议 30 分钟，覆盖"生成 -> 分享"的完整链路。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RoastRecord {

    /** 唯一 ID */
    private String roastId;

    /** 用户输入 */
    private String userInput;

    /** AI 生成的骂醒文案 */
    private String content;

    /** 使用的风格 */
    private RoastStyle style;

    /** 用户 openid（可选） */
    private String openid;

    /** 使用的 AI provider */
    private String provider;

    /** 创建时间 */
    private LocalDateTime createdAt;
}
