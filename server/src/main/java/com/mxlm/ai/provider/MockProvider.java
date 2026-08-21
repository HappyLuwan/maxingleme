package com.mxlm.ai.provider;

import cn.hutool.core.util.RandomUtil;
import com.mxlm.ai.AIProvider;
import com.mxlm.ai.ChatRequest;
import com.mxlm.ai.ChatResponse;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Mock Provider：本地开发用，不真实调用 AI
 * <p>
 * 使用方式：在 application-local.yml 里把 ai.default-provider 改为 mock
 */
@Component("mock")
public class MockProvider implements AIProvider {

    private static final List<String> MOCK_RESPONSES = List.of(
            "醒醒吧朋友！你这不是心动，你这是习惯性 emo。当断不断，反受其乱。",
            "我说你咋这么虎呢？这明明就是老套路，你还上头？赶紧的，把这事放一边，去干点正经的！",
            "宝贝，你已经很棒了，但更棒的自己在前方。放下这些烦恼，往前看，你会发现天地宽阔。",
            "从来如此，便对么？醒醒，别再陷在里面了。",
            "你冷静想一想：一年后，这件事还重要吗？答案很明显，对吧。",
            "别把生活过成一部苦情剧，主角光环得靠自己发光。"
    );

    @Override
    public String getKey() {
        return "mock";
    }

    @Override
    public String getName() {
        return "Mock 模拟器（本地开发用）";
    }

    @Override
    public boolean isAvailable() {
        return true;
    }

    @Override
    public ChatResponse chat(ChatRequest request) {
        String content = RandomUtil.randomEle(MOCK_RESPONSES);
        return ChatResponse.builder()
                .content(content)
                .model("mock-model")
                .provider("mock")
                .promptTokens(50)
                .completionTokens(30)
                .totalTokens(80)
                .costMillis(100L)
                .build();
    }
}
