# 骂醒了么 · 项目现状备忘录 (CONTEXT.md)

> 📌 **本文档用途**：新对话开始时，让 AI 快速掌握项目全貌，避免重复解释。
> 📅 **最后更新**：2026-08-28

---

## 一、项目一句话概述

**「骂醒了么」** 是一款情绪价值向的微信小程序 —— 用户输入困扰，后端从预置的人工创作文案库（10 个主题标签，5 风格 × 60 条 = 300 条金句）中匹配最贴合的一条返回，一键生成分享卡片传播裂变。

> ⚠️ **重要声明**：本项目仅使用本地预置文案库，**不使用任何生成式 AI / 深度合成技术**（因个人主体尚未开放此类目）。若未来主体升级，可循 `LocalProvider` 抽象层低成本切回 AI 模式。

---

## 二、技术栈

| 层 | 技术选型 |
|---|---|
| 前端 | 微信小程序原生（无框架） |
| 后端 | **Python 3.12 + FastAPI + Playwright + Jinja2**（Java 版已删除） |
| 文案引擎 | 本地精选文案库（300 条） + 关键词标签匹配，**不使用任何外部生成式服务** |
| 部署 | 微信云托管 CloudBase Run（走 `wx.cloud.callContainer`，不走 `wx.request`） |
| 卡片渲染 | Playwright 无头 Chromium 截图 |

---

## 三、目录结构

```
wechat-demo/
├── miniprogram/                # 前端
│   ├── pages/
│   │   ├── index/              # 首页（输入 + 风格选择）
│   │   ├── result/             # 结果页（文案 + 卡片 + 分享 + ❤收藏）
│   │   ├── mine/               # ⭐我的（tabBar 第 2 项，历史/收藏）
│   │   ├── about/              # 关于（tabBar 第 3 项）
│   │   ├── agreement/          # 用户协议
│   │   └── privacy/            # 隐私政策
│   ├── utils/
│   │   ├── api.js              # 走 wx.cloud.callContainer
│   │   └── config.js           # cloudEnv/cloudService/apiBaseUrl
│   ├── app.js/json/wxss
│   └── project.config.json
├── server-py/                  # 后端
│   ├── app/
│   │   ├── enums.py            # ★ 风格 & 模板的权威定义
│   │   ├── prompts.py          # 6 种风格 Prompt
│   │   ├── roast.py            # /api/roast（custom 风格短路 + 每日限流 + openid 写库）
│   │   ├── card.py             # /api/card
│   │   ├── history.py          # /api/history · /api/favorite · /api/user/stats（新增）
│   │   ├── user.py             # openid 依赖注入（从 Header 读 x-wx-openid）
│   │   ├── db.py               # 数据库层（MySQL 连接池 + SQLite 本地兜底）
│   │   ├── cleanup.py          # 定时清理任务（12h 一次）
│   │   ├── security.py         # 敏感词 + 心理危机词引导
│   │   ├── ai/                 # Provider 抽象 + Router + fallback
│   │   ├── analytics.py        # 卡片埋点（generate/save/share）+ /admin/card/stats
│   │   ├── admin.py            # 后台管理接口（AI 切换 + 概览 + 吐槽查询，全部脱敏）
│   │   ├── mask.py             # 数据脱敏工具（openid/手机号/身份证等自动打码）
│   │   ├── static/admin.html   # ⭐ 运营后台单页 UI（4 Tab：概览/卡片/吐槽/Provider）
│   │   ├── config.py           # 环境变量与运行时配置
│   │   ├── common.py           # Result/ErrorCode/异常
│   │   ├── repository.py       # 数据仓库（records/favorites/rate_limits 三表，MySQL/SQLite 双方言）
│   │   └── playwright_pool.py  # 无头浏览器单例池
│   │   # 数据表（db.py）：roast_records / favorites / rate_limits / card_events
│   ├── templates/              # 卡片 HTML 模板（对话截屏 + 8 套实验款）
│   │   ├── card-chat.html      # 对话截屏（默认、上线稳定款）
│   │   ├── card-checkin.html   # 清醒打卡（实验）
│   │   ├── card-rx.html        # 醒神药方（实验）
│   │   ├── card-wrapped.html   # 年终盘点（实验）
│   │   ├── card-comment.html   # 树洞回响（实验）
│   │   ├── card-news.html      # 社论快报（实验）
│   │   ├── card-note.html      # 便利贴纸（实验）
│   │   ├── card-track.html     # 单曲循环（实验）
│   │   └── card-tarot.html     # 塔罗指引（实验）
│   ├── main.py                 # FastAPI 入口
│   ├── Dockerfile
│   ├── cloudbaserun.yaml
│   └── .env.example
├── README.md                   # 项目总览
├── DEPLOY.md                   # 部署指引
├── REVIEW_GUIDE.md             # 小程序提交审核话术（知识库）
├── LAUNCH_CHECKLIST.md         # 上线前最后一公里可勾选清单 ⭐
├── scripts/
│   └── self_check.sh           # 本地/生产环境一键自测（13 项用例）
└── CONTEXT.md                  # 本文档
```

---

## 四、核心功能与业务规则

### 4.1 骂醒风格（6 种，权威源：`server-py/app/enums.py`）

| Key | 名称 | Emoji | 定位 | 是否匹配文案库 |
|---|---|---|---|---|
| `yiju` | 一针见血 | 💥 | 一句话暴击，推荐分享 | ✅ |
| `yinyang` | 阴阳怪气 | 😏 | 阴阳怪气小天才 | ✅ |
| `wenrou` | 温柔姐姐 | 🌸 | 温柔知性，直击心底 | ✅ |
| `luxun` | 鲁迅式 | 📜 | 深刻犀利，字字诛心 | ✅ |
| `zhexue` | 哲学家 | 🌙 | 从哲学高度让你顿悟 | ✅ |
| `custom` | 自定义 | ✍️ | 用户输入什么，卡片就是什么 | ❌ 短路，直接返回原文 |

**默认风格**：`yiju`。
**已废弃**（不要再引用）：`dushe`（毒舌闺蜜）、`dongbei`（东北大姐）。

### 4.2 卡片模板

**9 套正式款**（全部上线，按吸引力顺序排列，前 3 张最抓眼）：

| # | Key | 名称 | 视觉 |
|---|---|---|---|
| 1 | `tarot`   | 塔罗指引 | 深紫渐变 + 星辰几何，神秘感拉满（**全局默认**）|
| 2 | `rx`      | 醒神药方 | 处方笺 + 红章 + 条形码，反差萌 |
| 3 | `wrapped` | 年终盘点 | 网易云年度报告风渐变 + 数据卡 |
| 4 | `checkin` | 清醒打卡 | 打卡本 + 情绪分数条 |
| 5 | `track`   | 单曲循环 | 音乐播放器 UI + 时长 |
| 6 | `news`    | 社论快报 | 报纸头版 + 大标题 |
| 7 | `chat`    | 对话截屏 | 仿 iOS iMessage 气泡（万能兜底） |
| 8 | `comment` | 树洞回响 | 匿名评论区风格 |
| 9 | `note`    | 便利贴纸 | 便签纸手写字 |

**默认选中**：结果页首次进入自动生成 **`tarot`**（首屏最具吸引力）；后端 `get_card_template()` 兜底仍为 `chat`（万能不违和）。

**已删除**：`punch`（金句海报）、`poster`（语录海报）、`attack`（暴击语录）。

### 4.3 卡片埋点与数据分析

**埋点事件类型**（3 种）：

| Event | 触发时机 | 埋点方 |
|---|---|---|
| `generate` | 卡片生成成功（包含首次自动生成与手动切换）| 后端 `card.py` 自动 |
| `save` | 用户保存到相册成功 | 前端 `result.js` |
| `share` | 弹出分享面板（右上角胶囊 / 分享朋友圈）| 前端 `result.js` |

**存储**：`card_events` 表（openid / roast_id / template / event / created_at）。

**前端接口**：`POST /api/track/card`，静默失败，不阻塞主链路。

**后台查询**：`GET /admin/card/stats?days=7`（需 `X-Admin-Token`），返回各模板的生成/保存/分享数以及保存率、分享率，按 generate 降序。

**限制**：`share` 事件无法区分“点了分享”和“真实发送”（微信小程序 API 限制），实际上只能捕获到“点击分享事件”。

### 4.4 运营后台（Admin UI）

**入口**：`https://<云托管域名>/admin.html`，首次访问弹框输入 `ADMIN_TOKEN`（存 localStorage）。

**4 个 Tab**：

| Tab | 功能 | 后端接口 |
|---|---|---|
| 📊 概览 | 总用户 / 总骂醒 / 今日骂醒 / 总收藏 / 今日新增用户 + 当前 Provider | `GET /admin/overview` |
| 🎴 卡片数据 | 各模板生成/保存/分享数、保存率、分享率 | `GET /admin/card/stats?days=N` |
| 💬 用户吐槽 | 分页列表（脱敏视图），按时间/风格/仅收藏筛选，点"详情"看单条 | `GET /admin/records` · `GET /admin/records/{id}?full=0/1` |
| ⚙️ Provider | 文案库 provider 状态 | `GET /admin/ai/providers` |

**脱敏原则**（`mask.py`）：
- openid：`test-user-1-abc123def456` → `test****f456`
- 手机号（11 位 1 开头）→ `***`
- 身份证 / 邮箱 / 微信号 / QQ / 银行卡 → `***`
- 列表默认预览 50 字截断，详情默认 200 字截断，`?full=1` 展示完整文本（仍打码敏感数字）

**鉴权**：所有 `/admin/*` 接口都要求 `X-Admin-Token` Header，与 `ADMIN_TOKEN` 环境变量一致。

---

## 五、关键技术决策 & 踩坑记录

### 5.1 Google Fonts 外链已全部移除 ⚠️
- **原因**：云托管容器访不到 `googleapis.com`，Playwright `wait_until=networkidle` 会一直等直到 60s 硬超时，导致卡片生成失败（文艺语录风失败率最高）。
- **修复**：3 个卡片模板全部改用系统内置字体（Songti SC / STKaiti / PingFang SC）；`playwright_pool.py` 中拦截所有 Google 域名请求 `route.abort()`，等待策略降为 `domcontentloaded`。

### 5.2 响应式布局用 `vh`（方案A）
- 首页 & 结果页的**纵向间距**（page/header/wrap 的上下 padding、区块 margin-bottom）已全部改为 `vh`。
- **横向尺寸和内部小间距仍用 `rpx`**（rpx 已由小程序按屏宽 750 自动缩放）。
- 只有卡片圆角、边框、阴影、字号、底部安全区继续用 `rpx`。

### 5.3 微信小程序 button 的坑
- ❌ 不要给 button 加 `loading` 属性（哪怕值是 false 也会占位，导致文字不居中）。
- ✅ 用文案（如 `正在骂醒你...`）表达加载态。
- ✅ `.action-btn` 必须 `padding: 0 !important` + flex 居中，才能覆盖全局 `.g-btn` 的默认 padding。

### 5.4 后端接口调用方式
- **生产**：走 `wx.cloud.callContainer`（`utils/api.js` 已封装），不走 `wx.request`。
- **本地调试**：`config.js` 里 `useCloudContainer: false`，走 `apiBaseUrl: http://localhost:8080` + 开发者工具"不校验合法域名"。

### 5.5 自定义风格短路
- `style=custom` 时，`roast.py` 跳过文案匹配，直接把 `userInput` 作为 `content` 返回，`provider=custom`, `cost_millis=0`。

### 5.6 统一响应格式
- `Result { code, message, data }`，HTTP 状态永远 200，业务成败通过 `code` 区分（0 = 成功）。
- 错误码定义在 `common.py::ErrorCode`。

### 5.7 用户体系（openid + MySQL）
- **身份识别**：微信云托管自动往 Header 塞 `X-WX-OPENID`；本地开发用 `X-Openid` Header 兜底（`api.js` 里生成一个 `local-xxx` 存 storage 复用）
- **存储**：默认云托管 MySQL；`DB_BACKEND=mysql|sqlite` 切换；本地开发无 MySQL 时可切 sqlite 走 `./data/mxlm.db`
- **连接参数**：`DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME/DB_POOL_SIZE`
- **SQL 方言**：`db.py` 提供 `upsert_records_sql()` / `insert_favorite_sql()` / `upsert_rate_limit_sql()` / `ph()` 统一屏蔽方言差异，业务代码无感切换
- **三张表**：
  - `roast_records`：所有骂醒记录（openid + user_input + content + style + provider + created_at）
  - `favorites`：收藏（openid + roast_id 组合主键）
  - `rate_limits`：每日限流计数（openid + day）
- **业务策略**（`repository.py` 常量）：
  - `HISTORY_RETENTION_DAYS = 90`：历史保留 90 天
  - `HISTORY_MAX_PER_USER = 500`：单用户最多 500 条历史（收藏不受限）
- `DAILY_ROAST_LIMIT = 20`：每人每天最多 20 次骂醒
- **定时清理**：`cleanup.py` 用 threading.Timer 每 12h 跑一次 `cleanup_expired`
- **接口清单**：
  - `POST /api/roast`（改造：加 openid + 限流）
  - `GET /api/roast/quota`（新增：查今日剩余次数）
  - `GET /api/history?page&size` · `DELETE /api/history/{id}`
  - `POST /api/favorite/{id}` · `DELETE /api/favorite/{id}` · `GET /api/favorites?page&size`
  - `GET /api/user/stats`（首页统计小卡片用）
- **多实例支持**：MySQL 后端天然支持多实例并发；云托管实例数不再受 Min=Max=1 限制

---

## 六、合规 & 上线相关（已完成）

- ✅ **敏感词过滤**（`security.py`）：政治/领导人/自残/极端辱骂/涉黄涉暴/诽谤诱导；心理危机词返回全国心理援助热线 `400-161-9995` 引导。
- ✅ **用户协议**：`pages/agreement/`
- ✅ **隐私政策**：`pages/privacy/`（符合《个保法》《生成式 AI 服务管理暂行办法》，2026-08-28 更新，明示 openid 收集、90 天保留期、运营访问脱敏原则）
- ✅ **免责声明**（首页 + 结果页底部统一文案）：
> ⚠️ 文案均为人工创作，仅供娱乐，危险情况请寻求救助
- ✅ **关于页**（`pages/about/`）：备案号占位 `ICP备xxxxxxxx号-xX`、意见反馈入口、心理援助热线复制。
- ✅ **App 首次进入弹窗**：引导阅读用户协议 + 隐私政策，同意后本地缓存版本号（`app.js` PRIVACY_VERSION，隐私政策实质变更时递增以触发重新同意）。
- ✅ **REVIEW_GUIDE.md**：审核话术（类目建议"工具-效率"、服务描述学术化包装、拒审申诉模板）。

---

## 七、后续待办

- [x] **ICP 备案**（已完成，备案号：陕ICP备2026023416号-1X，已填入 `pages/about/about.js`）
- [x] **微信小程序主体认证**（已完成）
- [ ] **配置服务器域名白名单**（云托管域名加到 mp 后台）
- [ ] **添加体验成员**（最多 90 人，让朋友先试用）
- [ ] **云托管 MySQL 开通 + 环境变量配置**（数据持久化，详见 DEPLOY.md 第五章）
- [ ] **正式发布审核**（备案通过后提交）
- [x] 微信内容安全 API 接入（本地词库 + msgSecCheck 双保险）
- [ ] （可选）广告变现

---

## 八、常用命令速查

### 后端本地启动
```bash
cd server-py
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env  # 默认值已可直接跑
源 .env && uvicorn main:app --reload --port 8080
```

### 后端部署到云托管
```bash
# 打包（DEPLOY.md 已经把 zip 名写成 maxingleme-server.zip，与旧 Java 版无关）
cd server-py && zip -r ../maxingleme-server.zip . -x "__pycache__/*" -x ".venv/*" -x ".idea/*" -x ".env"
# 然后在 mp 后台 → 云托管 → 上传本地代码
```

### 后台管理
- URL：`https://<云托管域名>/admin.html`
- 默认 Token：`mxlm-admin-2026`（生产环境务必改成强密码）
- 4 个 Tab：概览 / 卡片数据 / 用户吐槽（脱敏）/ Provider 切换
- 数据脱敏：openid、手机号、身份证、邮箱等自动打码，运营人员看不到明文

---

## 九、如何让新对话的 AI 快速接手

**新对话第一句话建议**：
```
这是一个已在开发中的微信小程序项目「骂醒了么」。
请先阅读 CONTEXT.md 了解项目现状与关键决策，然后我们继续。
```

若需上线相关工作，请参考 [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)（自查清单 + MySQL 配置 + 提审话术 + 自测脚本）。

AI 读完这份文档后，应能立刻掌握：
- 前端在 `miniprogram/`、后端在 `server-py/`（Python）
- 6 种风格、3 套模板的完整定义
- 已完成合规工作 & 待办清单
- Google Fonts 已移除、vh 响应式、button padding 等历史踩坑
