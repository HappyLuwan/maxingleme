
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
- 服务名：`flask-ejik`（**必须和 `miniprogram/utils/config.js` 里的 `cloudService` 完全一致，当前项目已配为此值**）
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
   zip -r ../flask-ejik.zip . -x "__pycache__/*" -x ".venv/*" -x ".idea/*" -x ".env"
   ```
2. 进入云托管 → 选择服务 `flask-ejik` → **版本管理** → **新建版本**
3. 上传方式选 **"本地代码"** → 选择刚才的 `flask-ejik.zip`
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
   | `WX_MSG_SEC_CHECK_ENABLED` | `true` | 微信 msgSecCheck 兜底（云托管免 token，免费） |
   | `DB_BACKEND` | `mysql` | 存储后端，生产必须走 MySQL |
   | `DB_HOST` | `10.x.x.x` | 云托管 MySQL 内网 IP（在数据库详情里看） |
   | `DB_PORT` | `3306` | 端口 |
   | `DB_USER` | `root` | 数据库账号 |
   | `DB_PASSWORD` | `你设置的密码` | ⚠️ 强密码，别用弱口令 |
   | `DB_NAME` | `mxlm` | 数据库名（下面第五章会建） |

6. **点"提交"**，等待构建（首次约 3-5 分钟，后续增量构建 1-2 分钟）
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
  cloudEnv: 'prod-d6g8qda601a1eddc7',  // 【替换】刚才记下的环境 ID（当前项目已预填）
  cloudService: 'flask-ejik',          // 服务名，必须与云托管控制台完全一致
  useCloudContainer: true,             // 生产环境必须为 true
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
- 检查 `cloudService` 是否等于云托管服务名 `flask-ejik`
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

### Q6：想切换 AI 供应商 / 查看用户数据
- 部署完成后，云托管 → 服务 → **公网访问** → 开启（会给一个 `https://xxx.service.tcloudbase.com` 的域名）
- 浏览器打开 `https://xxx.service.tcloudbase.com/admin.html`
- 输入 `ADMIN_TOKEN` 后进入 4 Tab 后台：
  - 📊 **概览**：总用户 / 总骂醒 / 今日骂醒 / 总收藏 / 今日新增用户 + 当前 Provider
  - 🎴 **卡片数据**：9 套模板的生成 / 保存 / 分享数与保存率 / 分享率
  - 💬 **用户吐槽**：分页浏览用户输入与 AI 回复（**openid、手机号、身份证等自动脱敏**），可按时间/风格/仅收藏筛选，"详情"按钮可切换脱敏/完整模式
  - ⚙️ **Provider**：一键切换主力 / 兜底 AI 模型
- ⚠️ 生产上必须把 `ADMIN_TOKEN` 改为强密码，别用默认的 `mxlm-admin-2026`

---

## 五、云托管 MySQL 数据持久化（用户体系必读）⚠️

从 v1.1 版本起，后端引入了用户历史/收藏/限流的持久化存储。生产环境**必须使用云托管 MySQL**，容器本地数据会随重启丢失。

### 1. 开通云托管 MySQL

- 云托管控制台 → 左侧菜单 **数据库 / MySQL** → **创建实例**
- 版本：**MySQL 5.7 或 8.0**（本项目已在 5.7 验证）
- 规格：入门级 1核1G（月费约 20-50 元）即可，MVP 阶段足够
- 网络：**必须选和云托管服务相同的 VPC**（默认选项一般就对）
- 设置 root 密码：⚠️ **强密码**（不少于 12 位，包含大小写数字符号）
- 创建完成后记下**内网地址**（形如 `10.18.100.131:3306`）

### 2. 创建业务数据库 & 授权

云托管 MySQL 提供了 Web SQL 控制台（"实例详情 → 数据管理"），或用任意 MySQL 客户端连接内网地址后执行：

```sql
CREATE DATABASE IF NOT EXISTS mxlm DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 可选：为业务单建低权限账号（生产强烈推荐，不要直接用 root）
CREATE USER 'mxlm_app'@'%' IDENTIFIED BY '你设置的强密码';
GRANT ALL PRIVILEGES ON mxlm.* TO 'mxlm_app'@'%';
FLUSH PRIVILEGES;
```

> ⚠️ 生产建议：不要用 root，为服务单独建 `mxlm_app` 账号，只对 `mxlm` 库授权。

### 3. 配置环境变量

在云托管服务的"环境变量"里补齐以下（第二章方式 A 的表格里已列出）：

| 变量名 | 值 |
|---|---|
| `DB_BACKEND` | `mysql` |
| `DB_HOST` | 你的 MySQL 内网 IP |
| `DB_PORT` | `3306` |
| `DB_USER` | `root` 或 `mxlm_app` |
| `DB_PASSWORD` | 你设置的密码 |
| `DB_NAME` | `mxlm` |
| `DB_POOL_SIZE` | `5`（默认足够，量大再调） |

### 4. 建表（自动）

服务启动时会自动执行 [db.py](server-py/app/db.py) 里的 `init_db()`，在 `mxlm` 库中创建三张表：
- `roast_records`：骂醒记录
- `favorites`：收藏
- `rate_limits`：每日限流计数

无需手动建表。

### 5. 验证连通性

方式 A：进入云托管容器 Shell（"实例列表 → 操作 → 登录容器"），执行：
```bash
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SHOW TABLES;"
# 预期能看到 favorites / rate_limits / roast_records 三张表
```

方式 B：观察启动日志，出现如下即成功：
```
[DB] MySQL 连接池就绪 host=10.18.100.131:3306 db=mxlm pool_size=5
[DB] 初始化完成 backend=mysql
```

### 6. 多实例部署（可选）

用 MySQL 后**不再有 SQLite 的单实例限制**：
- 云托管 → 服务 → **实例数配置** → Min=1, Max=按需（如 3）
- 峰值扩容、灰度发布都无压力

### ⚠️ 数据备份

云托管 MySQL 默认已开启每日自动备份（保留 7 天），你可以在实例详情里手动触发备份/恢复。**不需要自己写备份脚本**。

---

## 六、成本预估（DeepSeek + 云托管 + MySQL）

| 项目 | 单价 | MVP 阶段月消耗 |
|---|---|---|
| 云托管 1核1G | 首月免费，之后约 60 元/月 | ~60 元 |
| 云托管 MySQL 1核1G | 约 25-50 元/月 | ~30 元 |
| DeepSeek Chat | 0.001 元/千 tokens | 100 人 × 10 次 × 500 tokens ≈ 0.5 元 |
| **合计** | - | **约 90 元/月** |

> ⚠️ 上线拉流量后重点看：**DeepSeek 会成为主要成本**，1000 DAU 时可能到 100 元/月，考虑加缓存（相同 userInput 复用结果）。

---

## 七、下一步

- [ ] 部署 OK 后，在体验版打磨 3-5 天
- [ ] 把 Prompt 打磨得更"毒"（这是产品的护城河）
- [ ] 优化卡片模板（多几套风格，让用户想收集）
- [ ] 增加匿名点赞 / 热门榜（做社交货币）
- [x] 内容安全接入微信 msgSecCheck（避免违规下架）
- [ ] 走审核 → 正式发布
