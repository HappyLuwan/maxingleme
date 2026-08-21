package com.mxlm.roast.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 骂醒请求 DTO
 */
@Data
public class RoastRequestDTO {

    /** 用户输入的困扰内容 */
    @NotBlank(message = "先告诉我你的烦恼吧")
    @Size(max = 500, message = "话说得太多啦，简短一点吧")
    private String userInput;

    /** 骂醒风格 key（dushe / dongbei / wenrou），不传默认 dushe */
    private String style;

    /** 用户 openid（可选，用于统计） */
    private String openid;
}
