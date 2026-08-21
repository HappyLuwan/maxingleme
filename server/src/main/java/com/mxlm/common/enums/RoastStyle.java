package com.mxlm.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

/**
 * 骂人风格枚举
 * <p>
 * 每种风格对应不同的 Prompt 人格。MVP 阶段先做 3 种，后续可扩展。
 */
@Getter
@AllArgsConstructor
public enum RoastStyle {

    /** 毒舌暴击型：犀利、一针见血、稍带刻薄 */
    DUSHE("dushe", "毒舌暴击", "🔥", "犀利如刀，一针见血"),

    /** 东北大姐型：豪爽、方言、又气又服 */
    DONGBEI("dongbei", "东北大姐", "🌶️", "东北大姐附体，让你听得又气又服"),

    /** 温柔姐姐型：温柔劝导、共情+引导 */
    WENROU("wenrou", "温柔姐姐", "🌸", "温柔知性，说到你心里去"),

    /** 鲁迅式（预留 V2） */
    LUXUN("luxun", "鲁迅式", "📜", "深刻犀利，字字诛心"),

    /** 哲学家式（预留 V2） */
    ZHEXUE("zhexue", "哲学家", "🌙", "从哲学高度让你顿悟"),

    /** 阴阳怪气型（预留 V2） */
    YINYANG("yinyang", "阴阳怪气", "😏", "阴阳怪气小天才");

    /** 风格 key，作为 API 传入参数 */
    private final String key;

    /** 风格显示名 */
    private final String displayName;

    /** 风格图标 emoji */
    private final String emoji;

    /** 风格描述 */
    private final String description;

    /**
     * 根据 key 获取枚举，找不到返回默认 DUSHE
     */
    public static RoastStyle fromKey(String key) {
        return Arrays.stream(values())
                .filter(s -> s.key.equalsIgnoreCase(key))
                .findFirst()
                .orElse(DUSHE);
    }

    /**
     * 判断 key 是否有效
     */
    public static boolean isValid(String key) {
        return Arrays.stream(values()).anyMatch(s -> s.key.equalsIgnoreCase(key));
    }
}
