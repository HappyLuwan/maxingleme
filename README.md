# 骂醒了么 🔥

> 你今天骂醒了么？—— 一个用 AI 帮你狠狠骂醒自己的微信小程序

## 📖 项目简介

「骂醒了么」是一款主打**情绪价值**的微信小程序，通过 AI 大模型生成不同风格的"骂醒"文案，帮用户在情感内耗、消费冲动、摆烂拖延等场景下清醒过来，并生成精美卡片方便分享传播。

## ✨ 核心特色

- 🎭 **多风格人格**：毒舌暴击 / 东北大姐 / 温柔姐姐 三大主力风格（可扩展）
- 🎨 **精美分享卡片**：3 套精心设计的卡片模板，自带传播力
- 🤖 **AI 模型可切换**：默认 DeepSeek，支持混元、豆包、通义千问，后台一键切换 + 自动兜底
- 🛡️ **内容安全**：本地敏感词过滤 + 微信内容安全 API（V2）
- ⚡ **零推广自然流量**：小程序名占词 + 分享卡片裂变

## 🏗️ 技术架构

前端（微信小程序原生）+ 后端（Spring Boot 3 + **LangChain4j** + Playwright + Thymeleaf）+ 多 AI Provider 策略模式切换。

> AI 调用层基于 [LangChain4j](https://github.com/langchain4j/langchain4j)（Java 版 LangChain），通过统一的 `ChatLanguageModel` 抽象接入所有 OpenAI 兼容的国产大模型（DeepSeek / 混元 / 豆包 / 通义千问），内置重试、超时、Token 统计。为未来扩展 memory / RAG / tools 打好基础。

## 📂 目录结构

```
wechat-demo/
├── server/                # Java Spring Boot 后端
│   ├── src/main/java/com/mxlm/
│   │   ├── ai/            # AI Provider 架构（策略模式）
│   │   ├── prompt/        # 3 套人格 Prompt
│   │   ├── roast/         # 骂醒核心业务
│   │   ├── card/          # 卡片生成 (Playwright)
│   │   ├── security/      # 内容安全
│   │   ├── admin/         # 后台管理
│   │   └── common/        # 通用组件
│   ├── src/main/resources/
│   │   ├── templates/     # 3 套 HTML 卡片模板
│   │   ├── static/        # 后台管理页
│   │   └── application*.yml
│   ├── Dockerfile
│   └── cloudbaserun.yaml
├── miniprogram/           # 微信小程序前端
│   ├── pages/index/       # 首页（输入 + 风格选择）
│   ├── pages/result/      # 结果页（展示 + 卡片 + 分享）
│   └── utils/             # API 封装 + 配置
└── README.md
```

## 🚀 快速开始

### 后端启动（本地开发）

```bash
cd server

# 首次运行：安装 Playwright 浏览器（下载 Chromium，约 200MB）
mvn exec:java -Dexec.mainClass="com.microsoft.playwright.CLI" -Dexec.args="install chromium"

# 启动服务（默认 local profile：Mock AI + H2 内存库，无需任何 API Key）
mvn spring-boot:run
```

访问：
- 后台管理页：http://localhost:8080/admin.html （默认 Token：`mxlm-admin-2026`）
- 健康检查：http://localhost:8080/actuator/health
- 骂醒 API：`POST http://localhost:8080/api/roast`

### 切换到真实 AI

1. 设置环境变量：`export DEEPSEEK_API_KEY=sk-xxx`
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

## 🎨 卡片模板

| 模板 | Key | 场景 | 特点 |
|-----|-----|------|-----|
| 聊天截图风 | `chat` | 传播王者 | 模仿微信聊天，一眼理解 |
| 暴击语录风 | `attack` | 情绪冲击 | 黑红渐变，大字号引言 |
| 海报文艺风 | `poster` | 文青必选 | 纸质背景，古典排版 |

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

## 📝 开发进度

- [x] AI Provider 可切换架构（DeepSeek/混元/豆包/通义/Mock）
- [x] 3 套风格 Prompt（毒舌 / 东北 / 温柔）
- [x] 骂醒核心接口 + 内容安全 + 心理危机词汇引导
- [x] 3 套精美卡片模板 + Playwright 生成
- [x] 后台管理页 + 一键切换
- [x] 小程序前端（首页 + 结果页 + 分享）
- [x] Dockerfile + 云托管配置
- [ ] 微信登录 + openid 用户体系
- [ ] 云开发数据库持久化（历史记录、榜单）
- [ ] 微信内容安全 API 接入
- [ ] 更多风格（鲁迅 / 哲学家 / 阴阳怪气）
- [ ] 广告变现

## 📄 License

MIT
