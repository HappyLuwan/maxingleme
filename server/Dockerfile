# ==========================================
# 骂醒了么后端服务 Dockerfile（多阶段构建）
# 部署平台：微信云托管 CloudBase Run
# 特殊要求：需要 Playwright + Chromium 依赖，故使用官方 Playwright 镜像
# ==========================================

# ---------- 阶段一：Maven 构建 ----------
FROM maven:3.9-eclipse-temurin-17-alpine AS builder

WORKDIR /build

# 先只拷 pom.xml，利用 Docker 层缓存加速依赖下载
COPY pom.xml .
RUN mvn dependency:go-offline -B --no-transfer-progress || true

# 拷源码 + 构建
COPY src ./src
RUN mvn clean package -DskipTests -B --no-transfer-progress

# ---------- 阶段二：运行时 ----------
# 使用 Playwright 官方镜像：已预装 Chromium + Node + Java 依赖
# 该镜像基于 Ubuntu Jammy，自带 Java 需另装
FROM mcr.microsoft.com/playwright/java:v1.42.0-jammy

WORKDIR /app

# 时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 拷贝可执行 jar
COPY --from=builder /build/target/maxingleme-server.jar app.jar

# JVM 参数（云托管建议 512M-1G）
ENV JAVA_OPTS="-Xms256m -Xmx768m -XX:+UseG1GC -Dfile.encoding=UTF-8"
ENV SPRING_PROFILES_ACTIVE=prod

# 创建卡片输出目录
RUN mkdir -p /data/mxlm-cards /data/logs

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD wget -qO- http://localhost:8080/actuator/health || wget -qO- http://localhost:8080/ || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
