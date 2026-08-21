package com.mxlm.ai;

/**
 * AI 大模型 Provider 统一接口
 * <p>
 * 所有 AI 服务实现都需实现此接口，通过 Spring 自动装配后由 {@link AIRouter} 统一调度。
 * <p>
 * 扩展新 Provider 步骤：
 * <ol>
 *   <li>实现本接口，用 @Component("providerKey") 注册</li>
 *   <li>在 application.yml 的 ai.providers 下增加配置</li>
 *   <li>可通过 /admin/ai/switch 后台切换启用</li>
 * </ol>
 */
public interface AIProvider {

    /**
     * Provider 唯一标识（如 "deepseek"、"hunyuan"）
     */
    String getKey();

    /**
     * Provider 显示名称（如 "DeepSeek Chat"）
     */
    String getName();

    /**
     * 当前是否可用（配置是否完整、是否 enabled）
     */
    boolean isAvailable();

    /**
     * 调用 AI 生成文本
     *
     * @param request 请求参数（含 system prompt 和 user input）
     * @return AI 响应
     */
    ChatResponse chat(ChatRequest request);
}
