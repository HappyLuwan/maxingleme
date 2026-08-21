package com.mxlm.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 错误码枚举
 */
@Getter
@AllArgsConstructor
public enum ErrorCode {

    // ==================== 通用错误 ====================
    SUCCESS(0, "成功"),
    SYSTEM_ERROR(500, "系统繁忙，请稍后再试"),
    PARAM_ERROR(400, "参数错误"),
    UNAUTHORIZED(401, "未授权"),
    FORBIDDEN(403, "无权访问"),
    NOT_FOUND(404, "资源不存在"),

    // ==================== 业务错误：10xxx ====================
    /** 输入内容违规 */
    CONTENT_ILLEGAL(10001, "内容包含违规信息，换一个说法试试～"),
    /** 输入内容过长 */
    CONTENT_TOO_LONG(10002, "话说得太多啦，简短一点吧"),
    /** 输入内容为空 */
    CONTENT_EMPTY(10003, "先告诉我你的烦恼吧"),
    /** 请求过于频繁 */
    RATE_LIMIT(10004, "骂太快了，喘口气再来～"),

    // ==================== AI 相关错误：11xxx ====================
    AI_PROVIDER_NOT_FOUND(11001, "AI 服务不存在"),
    AI_CALL_FAILED(11002, "AI 服务调用失败"),
    AI_TIMEOUT(11003, "AI 服务响应超时"),
    AI_ALL_PROVIDERS_FAILED(11004, "所有 AI 服务暂时不可用"),
    AI_RESPONSE_INVALID(11005, "AI 返回内容异常"),

    // ==================== 卡片相关错误：12xxx ====================
    CARD_TEMPLATE_NOT_FOUND(12001, "卡片模板不存在"),
    CARD_GENERATE_FAILED(12002, "卡片生成失败"),
    CARD_ROAST_NOT_FOUND(12003, "骂醒记录不存在"),

    // ==================== 微信相关错误：13xxx ====================
    WX_CONTENT_CHECK_FAILED(13001, "微信内容审核失败"),
    WX_API_ERROR(13002, "微信接口调用失败");

    private final Integer code;
    private final String message;
}
