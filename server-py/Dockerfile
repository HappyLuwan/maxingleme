# ==========================================
# 骂醒了么后端服务 Dockerfile
# 部署平台：微信云托管 CloudBase Run
#
# 基于 python:3.12-slim + Playwright 预装 Chromium：
#   - 镜像大小：~500MB
#   - 冷启动：3-5s
#   - 运行时内存：~500MB
# ==========================================

FROM python:3.12-slim-bookworm

# 时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Python 环境
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ---------- 第一步：安装 Python 依赖 ----------
# 单独 COPY requirements.txt 利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.tencent.com/pypi/simple \
    -r requirements.txt

# ---------- 第二步：安装 Chromium 及运行时依赖 ----------
# playwright install 会自动装 Chromium 到 /root/.cache/ms-playwright
# --with-deps 会自动装系统运行库（省去手动 apt-get 一大堆 lib）
# 只装 chromium 一个浏览器（跳过 Firefox / WebKit）
RUN playwright install --with-deps chromium && \
    # 额外装中文字体，保证卡片文字显示正常
    apt-get update && \
    apt-get install -y --no-install-recommends fonts-noto-cjk fonts-noto-color-emoji && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# ---------- 第三步：拷贝应用代码 ----------
COPY app/ ./app/
COPY templates/ ./templates/
COPY main.py .

# 卡片输出目录
RUN mkdir -p /tmp/mxlm-cards

# ---------- 运行 ----------
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/actuator/health').read()" || exit 1

# uvicorn 生产模式：单 worker（Playwright 浏览器池是单例，多 worker 会重复启动）
# 如需高并发，可用 gunicorn + uvicorn worker，但需重新设计 Playwright 池
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
