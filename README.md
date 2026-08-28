# 骂醒了么 🔥

> 你今天骂醒了么？—— 一个用 AI 帮你狠狠骂醒自己的微信小程序

## 📖 项目简介

「骂醒了么」是一款主打**情绪价值**的微信小程序，通过 AI 大模型生成不同风格的"骂醒"文案，帮用户在情感内耗、消费冲动、摆烂拖延等场景下清醒过来，并生成精美卡片方便分享传播。

## ✨ 核心特色

- 🎭 **6 种骂醒风格**：一针见血 / 阴阳怪气 / 温柔姐姐 / 鲁迅式 / 哲学家 / 自定义
- 🎨 **3 套分享卡片**：金句海报 / 聊天截图 / 海报文艺，自带传播力
- 🤖 **AI 模型可切换**：默认 DeepSeek，支持混元、豆包、通义千问，后台一键切换 + 自动兜底
- 🛡️ **内容安全**：本地敏感词过滤 + 微信内容安全 API + 心理危机词汇引导
- ⚡ **一键分享**：小程序名占词 + 分享卡片裂变

## 🏗️ 技术架构

前端（微信小程序原生）+ 后端（**Python 3.12 + FastAPI + Playwright + Jinja2**）+ 多 AI Provider 策略模式切换。

AI 调用层通过统一的 OpenAI 兼容抽象接入所有国产大模型（DeepSeek / 混元 / 豆包 / 通义千问），内置重试、超时、Token 统计与自动兜底。

## 📂 目录结构

```
wechat-demo/
├── server-py/                 # Python FastAPI 后端
│   ├── app/
│   │   ├── ai/                # AI Provider 架构（策略模式）
│   │   ├── prompts.py         # 6 种风格的 Prompt 模板
│   │   ├── roast.py           # 骂醒核心业务
│   │   ├── card.py            # 卡片生成 (Playwright)
│   │   ├── security.py        # 内容安全
│   │   ├── admin.py           # 后台管理
│   │   ├── enums.py           # 风格/模板枚举
│   │   ├── config.py          # 配置
│   │   ├── common.py          # 通用响应/异常
│   │   └── repository.py      # 骂醒记录存储
│   ├── templates/             # 3 套 HTML 卡片模板
│   ├── main.py                # FastAPI 入口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── cloudbaserun.yaml
├── miniprogram/               # 微信小程序前端
│   ├── pages/index/           # 首页（输入 + 风格选择）
│   ├── pages/result/          # 结果页（展示 + 卡片 + 分享）
│   ├── pages/about|agreement|privacy/  # 关于/协议/隐私
│   └── utils/                 # API 封装 + 配置
├── DEPLOY.md                  # 部署说明
├── REVIEW_GUIDE.md            # 小程序审核指南
└── README.md
```

## 🚀 快速开始

### 后端启动（本地开发）

```bash
cd server-py

# 建议 Python 3.12
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 首次运行：安装 Playwright 浏览器（Chromium，约 200MB）
python -m playwright install chromium

# 复制并配置环境变量
cp .env.example .env

# 启动服务（默认无 API Key 时走 Mock）
uvicorn main:app --reload --port 8080
```

访问：
- 后台管理页：http://localhost:8080/admin.html （默认 Token：`mxlm-admin-2026`）
- 健康检查：http://localhost:8080/health
- 骂醒 API：`POST http://localhost:8080/api/roast`

### 切换到真实 AI

1. 在 `.env` 中配置：`DEEPSEEK_API_KEY=sk-xxx`
2. 通过后台管理页把 provider 从 `mock` 切换到 `deepseek`

### 小程序前端启动

1. 用**微信开发者工具**打开 `miniprogram/` 目录
2. 修改 `project.config.json` 里的 `appid`
3. 修改 `utils/config.js` 里的 `apiBaseUrl` 为后端地址
4. 详情 → 本地设置 → 勾选**"不校验合法域名"**
5. 编译预览

## 🎯 核心接口

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/api/roast` | POST | 骂醒 |
| `/api/roast/styles` | GET | 风格列表 |
| `/api/card` | POST | 生成卡片 |
| `/api/card/image/{fileName}` | GET | 卡片图片下载 |
| `/api/card/templates` | GET | 卡片模板列表 |
| `/admin/ai/providers` | GET | 列出所有 AI Provider（需 Token） |
| `/admin/ai/switch` | POST | 切换主用 Provider（需 Token） |
| `/admin/ai/switch-fallback` | POST | 切换兜底 Provider（需 Token） |
| `/admin/ai/test` | POST | 测试指定 Provider（需 Token） |

> 后台接口需在 Header 携带 `X-Admin-Token`

## 🎭 骂醒风格

| 风格 | Key | 定位 |
|-----|-----|------|
| 一针见血 | `yiju` | 一句话暴击，推荐分享传播 |
| 阴阳怪气 | `yinyang` | 阴阳怪气小天才，让你无从反驳 |
| 温柔姐姐 | `wenrou` | 温柔知性，直击心底最柔软处 |
| 鲁迅式 | `luxun` | 深刻犀利，字字诛心 |
| 哲学家 | `zhexue` | 从哲学高度让你顿悟 |
| 自定义 | `custom` | 用户自己输入文案，直接生成卡片（不调用 AI） |

## 🎨 卡片模板

**9 套正式款**（按吸引力排序，结果页横向滚动展示）：

`tarot` 🔮 → `rx` 💊 → `wrapped` 🎯 → `checkin` 📊 → `track` 💿 → `news` 📰 → `chat` 💬 → `comment` 🌙 → `note` 🗒

- **首屏默认**：`tarot`（塔罗指引，视觉冲击最强）
- **万能兜底**：`chat`（后端 `get_card_template()` 找不到 key 时默认返回）

**已删除**：`punch`（金句海报）、`poster`（语录海报）。

## 🤖 AI Provider 切换

**方式 1：后台管理页**（推荐）
- 访问 `/admin.html` → 输入 Token → 点击"设为主用"

**方式 2：API 调用**
```bash
curl -X POST http://localhost:8080/admin/ai/switch \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: mxlm-admin-2026" \
  -d '{"providerKey": "hunyuan"}'
```

## 📄 License

MIT
