package com.mxlm.security;

import cn.hutool.core.util.StrUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 内容安全服务
 * <p>
 * MVP 阶段：本地敏感词过滤（快速上线）
 * V2：接入微信内容安全 API（msg_sec_check）
 */
@Slf4j
@Service
public class ContentSecurityService {

    @Value("${wechat.miniapp.content-security.enabled:true}")
    private boolean enabled;

    /**
     * 本地敏感词库（简化版，MVP 用；生产建议接入 DFA 或第三方）
     */
    private static final List<String> LOCAL_BLACKLIST = List.of(
            // 政治、暴恐等（这里只列示例，实际部署时应用完整词库）
            "习近平", "毛泽东", "共产党", "法轮功", "达赖",
            // 色情低俗
            "做爱", "性交", "自慰",
            // 违法犯罪
            "自杀", "自残", "杀人", "吸毒", "毒品", "赌博",
            // 极端负面情绪（涉及需要专业心理干预的关键词）
            "想死", "不想活", "轻生", "跳楼", "割腕"
    );

    /**
     * 检测用户输入是否安全
     *
     * @param text 待检测文本
     * @return 检测结果
     */
    public CheckResult check(String text) {
        if (StrUtil.isBlank(text)) {
            return CheckResult.pass();
        }
        if (!enabled) {
            return CheckResult.pass();
        }
        String lower = text.toLowerCase();
        for (String word : LOCAL_BLACKLIST) {
            if (lower.contains(word.toLowerCase())) {
                log.warn("[ContentSecurity] 命中敏感词: {}, text preview: {}",
                        word, StrUtil.maxLength(text, 30));

                // 心理危机词汇特殊处理：返回引导求助
                if (isCrisisWord(word)) {
                    return CheckResult.crisis(word);
                }
                return CheckResult.block(word);
            }
        }
        return CheckResult.pass();
    }

    private boolean isCrisisWord(String word) {
        return List.of("想死", "不想活", "轻生", "跳楼", "割腕", "自杀", "自残").contains(word);
    }

    /**
     * 检测结果
     */
    public record CheckResult(boolean passed, boolean crisis, String hitWord, String message) {

        public static CheckResult pass() {
            return new CheckResult(true, false, null, null);
        }

        public static CheckResult block(String word) {
            return new CheckResult(false, false, word,
                    "话里带了不太合适的词，换个说法试试？");
        }

        public static CheckResult crisis(String word) {
            return new CheckResult(false, true, word,
                    "看到你的话，我很担心你。请拨打 24 小时心理援助热线 400-161-9995，你不是一个人在扛。");
        }
    }
}
