
# 骂醒了么 · 微信云托管部署清单

> 目标：**30 分钟内把后端跑到微信云托管，手机上直接体验**  
> 前置：小程序 AppID 已注册（骂醒了么），并已把该 AppID 填入 `miniprogram/project.config.json`。

---

## 一、mp 后台一次性配置（10 分钟）

登录 [https://mp.weixin.qq.com/](https://mp.weixin.qq.com/) → 用小程序管理员扫码。

### 1. 开通微信云托管

- 左侧菜单 → **云开发** → **进入** → 顶部切到 **"云托管"** Tab
- 首次进入需**开通**，勾选服务协议、选择付费方式
- 会默认创建一个环境，比如 `prod-1g5xxxxxx`（**记下这个 envId**，前端要用）

> 💡 免费额度：新用户前 1 个月每天 3960 分钟 CPU、7920 分钟内存，MVP 阶段完全够用。

### 2. 新建服务

- 云托管首页 → **新建服务**
- 服务名：`maxingleme-server`（**必须和 `miniprogram/utils/config.js` 里的 `cloudService` 完全一致**）
- 备注：骂醒了么后端

### 3. 加体验成员

- 左侧菜单 → **管理** → **成员管理** → **体验成员** → 添加你自己的微信号  
  （不加成员的话，非管理员打开小程序会提示"未在体验成员列表"）

---

## 二、上传代码 + 部署（10 分钟）

云托管有两种上传方式，任选其一：

### 方式 A：本地 Zip 上传（**推荐，最快**）

1. **打包代码**（在项目根目录执行）
   ```bash
   cd /Users/breatche/code/wechat-demo/server-py
   zip -r ../maxingleme-server.zip . -x "__pycache__/*" -x ".venv/*" -x ".idea/*" -x ".env"
   ```
2. 进入云托管 → 选择服务 `maxingleme-server` → **版本管理** → **新建版本**
3. 上传方式选 **"本地代码"** → 选择刚才的 `maxingleme-server.zip`
4. **构建配置**：
   - Dockerfile 路径：`Dockerfile`（默认）
   - 端口：`8080`
   - 副本数：`0-2`（缩容到 0 更省钱；有稳定用户后改 1-2）
   - CPU / 内存：**`1 核 / 2G`**（Chromium 需要）
5. **环境变量**（点"添加环境变量"，逐个填）：

   | 变量名 | 值 | 说明 |
   |---|---|---|
   | `AI_ACTIVE_PROVIDER` | `deepseek` | 默认启用的 provider |
   | `AI_FALLBACK_PROVIDER` | `hunyuan` | 兜底 provider |
   | `DEEPSEEK_API_URL` | `https://api.deepseek.com/v1` | DeepSeek 官方 base_url |
   | `DEEPSEEK_API_KEY` | `sk-你自己申请的Key` | https://platform.deepseek.com/ |
   | `DEEPSEEK_MODEL` | `deepseek-chat` | 或 `deepseek-reasoner` |
   | `ADMIN_TOKEN` | `换一个强密码，例如 mxlm-x8k3f9` | 用于访问 `/admin.html` |
   | `CARD_OUTPUT_DIR` | `/tmp/mxlm-cards` | Dockerfile 里已建好 |

6. **点"提交"**，等待构建（Python 版首次约 3-5 分钟，比 Java 版快很多）
7. 构建成功后 → **版本管理** → 找到刚才的版本 → **发布**

### 方式 B：Git 仓库连接（自动化，适合后续迭代）

- 需先把代码推到 GitHub/Gitee
- 云托管 → 服务 → 新建版本 → **"代码仓库"** → 授权并选仓库
- **⚠️ 目标目录填 `server-py/`**（Python 版目录），Dockerfile 路径填 `Dockerfile`
- 剩下配置同方式 A

---

## 三、前端配置 + 真机体验（5 分钟）

### 1. 填 envId

编辑 [config.js](miniprogram/utils/config.js)：

```javascript
const config = {
  cloudEnv: 'prod-1g5xxxxxx',   // 【替换】刚才记下的环境 ID
  cloudService: 'maxingleme-server',
  useCloudContainer: true,      // 生产环境必须为 true
  requestTimeout: 30000
}
```

### 2. 微信开发者工具

- 打开 **微信开发者工具** → 导入项目 → 目录选 `/Users/breatche/code/wechat-demo/miniprogram`
- **右上角 → 详情 → 本地设置**：
  - ✅ 勾选 **"不校验合法域名..."** （体验期用，正式版可以不勾）
- 点 **编译** → 首页应该能看到风格列表加载出来
- 输入"我想复合" → 选个风格 → 骂醒 → 生成卡片 ✅

### 3. 真机预览

- 开发者工具 → **预览** → 手机微信扫二维码 → 在手机上完整跑一遍
- 走完 "输入 → 骂醒 → 生成卡片 → 保存到相册 → 分享给朋友" 完整闭环

---

## 四、常见坑 & 排查

### Q1：小程序调用报 `-501000` 或 `env not found`
- 检查 `config.js` 里的 `cloudEnv` 和云托管环境 ID 是否一致（大小写敏感）
- 检查 `app.js` 里 `wx.cloud.init` 是否成功执行（看 console）

### Q2：报 `service not found` 或 404
- 检查 `cloudService` 是否等于云托管服务名 `maxingleme-server`
- 云托管服务是否已"发布"（新建版本 ≠ 发布）

### Q3：构建卡在 Playwright 步骤 / 超时
- Python 版基于 `python:3.12-slim`，`playwright install chromium` 会下载约 150MB
- 如果超时，重试构建即可
- 也可以在 Dockerfile 里加国内 pip 镜像加速（已默认使用腾讯源）

### Q4：AI 一直返回 Mock 内容
- 检查 `DEEPSEEK_API_KEY` 是否配了、有余额
- 检查 `AI_ACTIVE_PROVIDER=deepseek` 是否设置正确
- 查看云托管日志确认 provider 加载情况（搜 `AIRouter` 关键字）

### Q5：卡片图不显示 / 一片空白
- Playwright 内存不够，把云托管内存调到 **至少 2G**
- 看云托管日志：搜 `CardService` 或 `PlaywrightPool` 关键字
- 首次启动 Playwright 初始化约需 3-5 秒，请求要预留超时

### Q6：想切换 AI 供应商
- 部署完成后，云托管 → 服务 → **公网访问** → 开启（会给一个 `https://xxx.service.tcloudbase.com` 的域名）
- 浏览器打开 `https://xxx.service.tcloudbase.com/admin.html`
- 输入 `ADMIN_TOKEN` → 一键切换 Provider

---

## 五、成本预估（DeepSeek + 云托管）

| 项目 | 单价 | MVP 阶段月消耗 |
|---|---|---|
| 云托管 1核1G | 首月免费，之后约 60 元/月 | ~60 元 |
| DeepSeek Chat | 0.001 元/千 tokens | 100 人 × 10 次 × 500 tokens ≈ 0.5 元 |
| **合计** | - | **约 60 元/月** |

> ⚠️ 上线拉流量后重点看：**DeepSeek 会成为主要成本**，1000 DAU 时可能到 100 元/月，考虑加缓存（相同 userInput 复用结果）。

---

## 六、下一步

- [ ] 部署 OK 后，在体验版打磨 3-5 天
- [ ] 把 Prompt 打磨得更"毒"（这是产品的护城河）
- [ ] 优化卡片模板（多几套风格，让用户想收集）
- [ ] 增加匿名点赞 / 热门榜（做社交货币）
- [ ] 内容安全接入微信 msgSecCheck（避免违规下架）
- [ ] 走审核 → 正式发布
