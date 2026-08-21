package com.mxlm.roast;

import cn.hutool.core.util.StrUtil;
import com.mxlm.ai.AIRouter;
import com.mxlm.ai.ChatRequest;
import com.mxlm.ai.ChatResponse;
import com.mxlm.common.BusinessException;
import com.mxlm.common.ErrorCode;
import com.mxlm.common.enums.RoastStyle;
import com.mxlm.prompt.PromptRegistry;
import com.mxlm.prompt.PromptTemplate;
import com.mxlm.roast.dto.RoastRequestDTO;
import com.mxlm.roast.dto.RoastResponseDTO;
import com.mxlm.security.ContentSecurityService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * 骂醒核心业务服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RoastService {

    private final AIRouter aiRouter;
    private final PromptRegistry promptRegistry;
    private final ContentSecurityService securityService;
    private final RoastRecordRepository recordRepository;

    /**
     * 骂醒
     */
    public RoastResponseDTO roast(RoastRequestDTO request) {
        // 1. 参数校验
        String userInput = request.getUserInput();
        if (StrUtil.isBlank(userInput)) {
            throw new BusinessException(ErrorCode.CONTENT_EMPTY);
        }
        userInput = userInput.trim();

        // 2. 内容安全检测
        ContentSecurityService.CheckResult checkResult = securityService.check(userInput);
        if (!checkResult.passed()) {
            if (checkResult.crisis()) {
                // 心理危机词汇：不走 AI，直接返回专业引导文案
                throw new BusinessException(ErrorCode.CONTENT_ILLEGAL, checkResult.message());
            }
            throw new BusinessException(ErrorCode.CONTENT_ILLEGAL, checkResult.message());
        }

        // 3. 解析风格
        RoastStyle style = RoastStyle.fromKey(request.getStyle());
        PromptTemplate promptTemplate = promptRegistry.get(style);

        // 4. 调用 AI
        ChatRequest chatRequest = ChatRequest.builder()
                .systemPrompt(promptTemplate.buildSystemPrompt())
                .userInput(userInput)
                .temperature(promptTemplate.getTemperature())
                .maxTokens(promptTemplate.getMaxTokens())
                .build();

        ChatResponse chatResponse = aiRouter.chat(chatRequest);
        String content = chatResponse.getContent();
        if (StrUtil.isBlank(content)) {
            throw new BusinessException(ErrorCode.AI_RESPONSE_INVALID);
        }

        // 5. 保存记录
        RoastRecord record = RoastRecord.builder()
                .userInput(userInput)
                .content(content)
                .style(style)
                .openid(request.getOpenid())
                .provider(chatResponse.getProvider())
                .build();
        record = recordRepository.save(record);

        log.info("[RoastService] roast success, id={}, style={}, provider={}, cost={}ms",
                record.getRoastId(), style.getKey(), chatResponse.getProvider(),
                chatResponse.getCostMillis());

        // 6. 组装响应
        return RoastResponseDTO.builder()
                .roastId(record.getRoastId())
                .content(content)
                .style(style.getKey())
                .styleName(style.getDisplayName())
                .styleEmoji(style.getEmoji())
                .provider(chatResponse.getProvider())
                .costMillis(chatResponse.getCostMillis())
                .build();
    }

    /**
     * 根据 ID 获取骂醒记录（生成卡片时用）
     */
    public RoastRecord getById(String roastId) {
        RoastRecord record = recordRepository.findById(roastId);
        if (record == null) {
            throw new BusinessException(ErrorCode.CARD_ROAST_NOT_FOUND);
        }
        return record;
    }
}
