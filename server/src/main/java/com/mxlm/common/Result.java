package com.mxlm.common;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;
import lombok.experimental.Accessors;

import java.io.Serializable;

/**
 * 统一响应结果
 *
 * @param <T> 数据类型
 */
@Data
@Accessors(chain = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Result<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 业务码：0 表示成功，非 0 表示失败 */
    private Integer code;

    /** 提示信息 */
    private String message;

    /** 返回数据 */
    private T data;

    /** 时间戳（毫秒） */
    private Long timestamp;

    public Result() {
        this.timestamp = System.currentTimeMillis();
    }

    public static <T> Result<T> success() {
        return success(null);
    }

    public static <T> Result<T> success(T data) {
        return new Result<T>()
                .setCode(0)
                .setMessage("success")
                .setData(data);
    }

    public static <T> Result<T> success(String message, T data) {
        return new Result<T>()
                .setCode(0)
                .setMessage(message)
                .setData(data);
    }

    public static <T> Result<T> fail(Integer code, String message) {
        return new Result<T>()
                .setCode(code)
                .setMessage(message);
    }

    public static <T> Result<T> fail(ErrorCode errorCode) {
        return new Result<T>()
                .setCode(errorCode.getCode())
                .setMessage(errorCode.getMessage());
    }

    public static <T> Result<T> fail(ErrorCode errorCode, String customMessage) {
        return new Result<T>()
                .setCode(errorCode.getCode())
                .setMessage(customMessage);
    }
}
