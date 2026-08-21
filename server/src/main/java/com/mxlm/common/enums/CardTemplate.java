package com.mxlm.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

/**
 * 卡片模板枚举
 */
@Getter
@AllArgsConstructor
public enum CardTemplate {

    /** 暴击语录风：大字号、渐变色、有冲击力 */
    ATTACK("attack", "card-attack", "暴击语录风"),

    /** 聊天截图风：模仿微信对话，传播性最强 */
    CHAT("chat", "card-chat", "聊天截图风"),

    /** 海报文艺风：留白多、有设计感 */
    POSTER("poster", "card-poster", "海报文艺风");

    private final String key;

    /** 对应的 Thymeleaf 模板文件名（不含扩展名） */
    private final String templateName;

    /** 显示名 */
    private final String displayName;

    public static CardTemplate fromKey(String key) {
        return Arrays.stream(values())
                .filter(t -> t.key.equalsIgnoreCase(key))
                .findFirst()
                .orElse(CHAT);
    }
}
