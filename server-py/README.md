# 骂醒了么 · 后端

**技术栈**：Python 3.12 + FastAPI + Playwright + Jinja2 + OpenAI SDK（兼容 DeepSeek/混元/豆包/通义）

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
│   ├── prompts.py           # 6 种风格的 Prompt 模板
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
    ├── card-chat.html       # 稳定款：iOS 深色 iMessage 聊天截图
    ├── card-checkin.html    # 实验款：清醒打卡
    ├── card-rx.html         # 实验款：清醒处方
    ├── card-wrapped.html    # 实验款：年度骂醒
    ├── card-comment.html    # 实验款：深夜留言板
    ├── card-news.html       # 实验款：骂醒日报
    ├── card-note.html       # 实验款：深夜便签
    ├── card-track.html      # 实验款：骂醒单曲
    └── card-tarot.html      # 实验款：清醒塔罗
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
- 健康检查：http://localhost:8080/health

### 4. 快速验证
```bash
curl -X POST http://localhost:8080/api/roast \
  -H 'Content-Type: application/json' \
  -d '{"userInput":"前任又来找我了，我心动了怎么办","style":"yiju"}'
```

## 🎭 支持的骂醒风格

| Key | 名称 | 定位 |
|---|---|---|
| `yiju` | 一针见血 | 一句话暴击，推荐分享 |
| `yinyang` | 阴阳怪气 | 阴阳怪气小天才 |
| `wenrou` | 温柔姐姐 | 温柔知性，直击心底 |
| `luxun` | 鲁迅式 | 深刻犀利，字字诛心 |
| `zhexue` | 哲学家 | 从哲学高度让你顿悟 |
| `custom` | 自定义 | 用户自输入，不调用 AI |

## 🔧 关键接口

- `POST /api/roast` — 一键骂醒
- `GET /api/roast/styles` — 风格列表
- `POST /api/card` — 生成卡片（返回 Base64）
- `GET /api/card/image/{fileName}` — 卡片图片
- `GET /admin/ai/providers` — 后台：Provider 列表（需 X-Admin-Token）
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

见根目录 [DEPLOY.md](../DEPLOY.md)。关键：GitHub 拉取时**目标目录填 `server-py/`**。
