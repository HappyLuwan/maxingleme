# 骂醒了么 · 后端

**技术栈**：Python 3.12 + FastAPI + Playwright + Jinja2

**服务说明**：本项目基于预置的人工创作文案库 + 关键词匹配算法提供服务，**不使用任何生成式 AI / 深度合成技术**。

## 🎯 项目结构

```
server-py/
├── main.py                  # FastAPI 入口 + 生命周期
├── requirements.txt         # Python 依赖
├── Dockerfile               # 部署镜像
├── cloudbaserun.yaml        # 微信云托管配置
├── .env.example             # 环境变量示例
├── app/
│   ├── config.py            # 应用配置
│   ├── common.py            # 统一响应/异常
│   ├── enums.py             # 风格枚举、卡片模板
│   ├── prompts.py           # 6 种风格的元数据（保留兼容层）
│   ├── security.py          # 敏感词过滤 + 心理危机词引导
│   ├── repository.py        # 记录仓库 + TTL
│   ├── playwright_pool.py   # 无头浏览器单例池
│   ├── roast.py             # 骂醒业务 + /api/roast
│   ├── card.py              # 卡片生成 + /api/card
│   ├── admin.py             # 后台管理
│   └── ai/
│       ├── base.py          # 文案 Provider 抽象接口
│       ├── local_lines.py   # 精选文案库（人工创作，5 风格 × 60 条）
│       ├── local_provider.py # 关键词匹配 + 文案选择
│       ├── providers.py     # 兼容工厂
│       └── router.py        # 路由（只挂载 LocalProvider）
└── templates/
    └── card-*.html          # 9 套分享卡片模板
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
# .env 里的默认值已经能直接跑，无需 API Key
```

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
| `custom` | 自定义 | 用户自输入 |

## 🔧 关键接口

- `POST /api/roast` — 一键骂醒
- `GET /api/roast/styles` — 风格列表
- `POST /api/card` — 生成卡片（返回 Base64）
- `GET /api/card/image/{fileName}` — 卡片图片
- `GET /admin/ai/providers` — 后台：Provider 列表（需 X-Admin-Token）

## 🐳 Docker 构建

```bash
docker build -t maxingleme:py .
docker run -p 8080:8080 maxingleme:py
```

## 🌈 部署到微信云托管

见根目录 [DEPLOY.md](../DEPLOY.md)。关键：GitHub 拉取时**目标目录填 `server-py/`**。
