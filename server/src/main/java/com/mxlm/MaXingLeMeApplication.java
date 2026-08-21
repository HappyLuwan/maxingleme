package com.mxlm;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * 骂醒了么 - 后端服务启动类
 *
 * @author mxlm
 */
@SpringBootApplication
@EnableCaching
@EnableAsync
// MVP 阶段暂不使用 MyBatis，未来接入数据库时打开：
// @MapperScan("com.mxlm.mapper")
public class MaXingLeMeApplication {

    public static void main(String[] args) {
        SpringApplication.run(MaXingLeMeApplication.class, args);
        System.out.println("""
                
                ╔══════════════════════════════════════╗
                ║   骂醒了么 服务启动成功 🔥            ║
                ║   你今天骂醒了么？                    ║
                ╚══════════════════════════════════════╝
                """);
    }
}
