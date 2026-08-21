package com.mxlm.roast;

import com.mxlm.common.Result;
import com.mxlm.common.enums.RoastStyle;
import com.mxlm.roast.dto.RoastRequestDTO;
import com.mxlm.roast.dto.RoastResponseDTO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

/**
 * 骂醒接口
 */
@RestController
@RequestMapping("/api/roast")
@RequiredArgsConstructor
public class RoastController {

    private final RoastService roastService;

    /**
     * 一键骂醒
     * <p>
     * POST /api/roast
     * body: { userInput, style, openid }
     */
    @PostMapping
    public Result<RoastResponseDTO> roast(@Valid @RequestBody RoastRequestDTO request) {
        return Result.success(roastService.roast(request));
    }

    /**
     * 获取所有可用风格列表（小程序首页展示用）
     * <p>
     * GET /api/roast/styles
     */
    @GetMapping("/styles")
    public Result<List<Map<String, Object>>> listStyles() {
        List<Map<String, Object>> styles = Arrays.stream(RoastStyle.values())
                .map(s -> Map.<String, Object>of(
                        "key", s.getKey(),
                        "name", s.getDisplayName(),
                        "emoji", s.getEmoji(),
                        "description", s.getDescription(),
                        // MVP 阶段只启用前 3 个
                        "enabled", isMvpEnabled(s)
                ))
                .toList();
        return Result.success(styles);
    }

    private boolean isMvpEnabled(RoastStyle style) {
        return style == RoastStyle.DUSHE
                || style == RoastStyle.DONGBEI
                || style == RoastStyle.WENROU;
    }
}
