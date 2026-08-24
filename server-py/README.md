# 骂醒了么 · 后端（Python 版）

**技术栈**：FastAPI + Playwright + Jinja2 + OpenAI SDK（兼容 DeepSeek/混元/豆包/通义）

## 🎯 项目结构

```
server-py/
├── main.py                  # FastAPI 入口 + 生命周期
├── requirements.txt         # Python 依赖
├── Dockerfile               # 部署镜像（约 500MB）
├── cloudbaserun.yaml        # 微信云托管配置
├── .env.example             # 环境变量示例
├── app/
│   ├── config.py            # 配置 + 运行时可切换 provider
│   ├── common.py            # 统一响应/异常
│   ├── enums.py             # 风格枚举、卡片模板
│   ├── prompts.py           # 3 套毒舌 Prompt（毒舌/东北/温柔）
│   ├── security.py          # 敏感词过滤 + 心理危机词引导
│   ├── repository.py        # 内存记录仓库 + TTL
│   ├── playwright_pool.py   # 无头浏览器单例池
│   ├── roast.py             # 骂醒业务 + /api/roast
│   ├── card.py              # 卡片生成 + /api/card
│   ├── admin.py             # 后台管理 + /admin/ai/*
│   └── ai/
│       ├── base.py          # AIProvider 抽象 + OpenAI 兼容基类
│       ├── providers.py     # DeepSeek/混元/豆包/通义 + Mock
│       └── router.py        # 路由 + 自动 fallback
└── templates/
    ├── card-attack.html     # 卡片模板 1：黑红渐变暴击风
    ├── card-chat.html       # 卡片模板 2：微信聊天截图风
    └── card-poster.html     # 卡片模板 3：米黄纸质海报风
```

## 🚀 本地快速启动

### 1. 创建虚拟环境 & 装依赖
```bash
cd server-py
python3.12 -m venv .venv
source .venv/bin/activate
pip install -i https://mirrors.tencent.com/pypi/simple -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
```

不填 API Key 也能跑 —— 会自动降级到 `MockProvider` 返回预置文案。

### 3. 启动
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

访问：
- Swagger 文档：http://localhost:8080/docs
- 健康检查：http://localhost:8080/actuator/health

### 4. 快速验证
```bash
curl -X POST http://localhost:8080/api/roast \
  -H 'Content-Type: application/json' \
  -d '{"userInput":"前任又来找我了，我心动了怎么办","style":"dushe"}'
```

## 📊 与 Java 版对比

| 维度 | Java 版 | Python 版 |
|---|---|---|
| 后端行数 | ~1500 行 | ~800 行 ✅ |
| 镜像大小 | ~900MB | ~500MB ✅ |
| 冷启动 | 15-30s | 3-5s ✅ |
| 运行时内存 | ~1.5GB | ~500MB ✅ |
| 云托管月成本 | ¥72 (1核2G) | ¥54 (0.5核2G) ✅ |
| Playwright 集成难度 | 高（浏览器池 + 版本坑） | 极低（官方 install） |
| LLM 生态 | LangChain4j（不成熟） | OpenAI SDK（事实标准） |

## 🔧 关键接口

小程序前端接口不变，与 Java 版**协议完全兼容**（同样字段、同样 code 返回）：

- `POST /api/roast` — 一键骂醒
- `GET /api/roast/styles` — 风格列表
- `POST /api/card` — 生成卡片（返回 Base64）
- `GET /api/card/image/{fileName}` — 卡片图片
- `GET /admin/ai/providers` — 后台：Provider 列表
- `POST /admin/ai/switch` — 后台：一键切换 active provider

## 🐳 Docker 构建

```bash
docker build -t maxingleme:py .
docker run -p 8080:8080 \
  -e DEEPSEEK_API_KEY=sk-xxx \
  -e AI_ACTIVE_PROVIDER=deepseek \
  maxingleme:py
```

## 🌈 部署到微信云托管

见根目录 [DEPLOY.md](../DEPLOY.md)。
关键：GitHub 拉取时**目标目录填 `server-py/`**（不再是 `server/`）。
