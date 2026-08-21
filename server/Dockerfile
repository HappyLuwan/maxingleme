# ==========================================
# 骂醒了么后端服务 Dockerfile（多阶段构建 · 精简版）
# 部署平台：微信云托管 CloudBase Run
# 优化目标：镜像大小从 4.18GB → 约 900MB
# 优化手段：
#   1. 运行时用轻量 JRE（而非 JDK）
#   2. 只安装 Chromium 一个浏览器（放弃 Firefox / WebKit）
#   3. 只装 Chromium 需要的系统依赖
# ==========================================

# ---------- 阶段一：Maven 构建 + Chromium 预下载 ----------
FROM maven:3.9-eclipse-temurin-17-alpine AS builder

WORKDIR /build

# 先只拷 pom.xml，利用 Docker 层缓存加速依赖下载
COPY pom.xml .
RUN mvn dependency:go-offline -B --no-transfer-progress || true

# 拷源码 + 构建
COPY src ./src
RUN mvn clean package -DskipTests -B --no-transfer-progress

# 预下载 Chromium 到指定目录（后续复制到运行时镜像）
# 这样运行时容器启动就不用再下载，冷启动更快
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mvn -B --no-transfer-progress exec:java \
        -Dexec.mainClass=com.microsoft.playwright.CLI \
        -Dexec.args="install chromium" \
        -Dexec.classpathScope=runtime \
    || echo "⚠️ 预下载失败，将在运行时首次调用时下载"

# ---------- 阶段二：运行时（轻量 JRE + Chromium） ----------
FROM eclipse-temurin:17-jre-jammy

WORKDIR /app

# 时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装 Chromium 运行所需的系统依赖 + 中文字体
# 说明：Playwright 官方镜像会装几百个包，这里只挑 Chromium 真正需要的
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget ca-certificates \
        libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 \
        fonts-noto-cjk fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Playwright 浏览器缓存目录（与 builder 保持一致）
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 从 builder 拷贝预下载好的 Chromium（若上一步下载成功）
COPY --from=builder /ms-playwright /ms-playwright

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
