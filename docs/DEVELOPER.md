# 开发者指南

> 帮助新接手的开发者快速理解项目结构，独立完成日常维护和功能开发。

---

## 一、项目概览

```
智能主板维修系统 v9.0 (团队版)
├── 后端: FastAPI + SQLAlchemy + SQLite/PostgreSQL      端口 8899
├── 前端: 单页 HTML (v7.4) + Vite/React (v2, 开发中)
├── AI:   DeepSeek / Kimi Code / Anthropic Claude
└── 部署: Docker Compose (PostgreSQL + 自动迁移)
```

**AI 对话流程（核心链路）：**

```
浏览器输入故障现象
  → 前端 fetch POST /api/chat  (HTML 第 3625-3644 行 callAI 函数)
  → chat_service.py 校验输入、加载会话历史、保存诊断记录
  → ai_proxy.py 根据平台转换格式 → 请求 AI API
  → SSE 流式返回 → 前端渲染 Markdown
```

---

## 二、目录结构速查

| 路径 | 作用 | 重要程度 |
|------|------|----------|
| `backend/app/main.py` | FastAPI 入口，注册路由/中间件/静态文件 | ⭐⭐⭐ |
| `backend/app/routers/chat.py` | `/api/chat` 聊天接口 | ⭐⭐⭐ |
| `backend/app/routers/admin.py` | 管理后台所有接口 + HTML 页面 | ⭐⭐⭐ |
| `backend/app/routers/auth.py` | 注册/登录/Token | ⭐⭐ |
| `backend/app/services/ai_proxy.py` | AI 平台对接（Kimi/DeepSeek/Claude） | ⭐⭐⭐ |
| `backend/app/services/chat_service.py` | 聊天业务逻辑（校验/会话/诊断） | ⭐⭐⭐ |
| `backend/app/services/config_service.py` | 加密存储 API Key（DB优先→.env兜底） | ⭐⭐ |
| `backend/app/services/auth.py` | JWT 生成/验证/密码哈希 | ⭐⭐ |
| `backend/app/config.py` | 全局配置（PydanticSettings 读 .env） | ⭐⭐ |
| `backend/app/database.py` | SQLAlchemy 引擎/会话/建表 | ⭐⭐ |
| `backend/app/models/*.py` | 数据模型（User/Diagnosis/Project/SystemConfig） | ⭐⭐ |
| `backend/app/middleware/security.py` | CSP/XSS/点击劫持安全头 | ⭐ |
| `backend/app/middleware/rate_limit.py` | 接口限流 | ⭐ |
| `backend/app/utils/crypto.py` | AES-256-GCM 加密（保护 API Key） | ⭐ |
| `backend/app/utils/validators.py` | 输入校验（XSS/SQL注入/长度限制） | ⭐ |
| `backend/tests/` | pytest 测试（94个用例） | ⭐⭐ |
| `mainboard_repair_system_v7.4_updated.html` | **主前端页面**（193KB 单文件） | ⭐⭐⭐ |
| `data/*.js` | 前端知识库（诊断规则/器件映射/案例库） | ⭐⭐ |
| `docs/nginx-https.conf` | Nginx HTTPS 反代模板 | ⭐ |
| `scripts/backup-db.sh` | 数据库备份脚本 | ⭐ |
| `scripts/restore-public.js` | 恢复脱敏数据 | ⭐ |
| `docker-compose.yml` | Docker 编排（PostgreSQL+后端+迁移） | ⭐⭐ |

---

## 三、环境搭建（5分钟）

```bash
# 1. 克隆
git clone https://github.com/LJQ-2027/mainboard-repair-system.git
cd mainboard-repair-system

# 2. 配置
cp .env.example .env
# 编辑 .env 填入 API Key 和 SECRET_KEY
# SECRET_KEY 生成：openssl rand -base64 48

# 3. 安装依赖
cd backend
pip install -r requirements.txt

# 4. 启动
python run.py --reload   # --reload 开发模式自动重启

# 5. 访问
# 主页:   http://localhost:8899
# API文档: http://localhost:8899/docs
# 管理后台: http://localhost:8899/admin/settings
```

---

## 四、常用操作

### 添加新的 AI 平台

编辑 `backend/app/services/ai_proxy.py`，在 `PROVIDERS` 字典中添加：

```python
PROVIDERS = {
    # 添加新平台...
    "new-platform": {
        "name": "新平台名称",
        "url": "https://api.new-platform.com/chat/completions",
        "key_prefix": "sk-new-",
        "models": ["model-1", "model-2"],
        "default_model": "model-1",
        "supports_vision": False,        # 是否支持图片
        "api_format": "openai",          # openai 或 anthropic
    },
}
```

然后在 `settings.html` 和主 HTML 的模型下拉框中添加新选项。

### 修改密码复杂度

编辑 `backend/app/schemas/user.py` 中的 `password_complexity` 验证器。

### 添加新的数据库表

```bash
# 1. 创建模型文件 backend/app/models/xxx.py
# 2. 在 backend/app/models/__init__.py 中注册
# 3. 生成迁移
cd backend
alembic revision --autogenerate -m "添加xxx表"
# 4. 应用迁移
alembic upgrade head
```

### 修改前端 AI 设置

编辑主 HTML 文件 `mainboard_repair_system_v7.4_updated.html`：
- 第 3471-3481 行: `getAISettings()` — AI设置的默认值
- 第 3625-3644 行: `callAI()` — 非流式AI调用
- 第 3570-3622 行: `callAIStream()` — 流式AI调用
- 第 3876-3975 行: `startAIDiagnosis()` — AI诊断入口
- 第 4319 行后: 登录/注册弹窗和逻辑

### 运行测试

```bash
# 后端（必须设置 PYTHONUTF8=1，Windows中文路径）
PYTHONUTF8=1 python -m pytest backend/tests/ -v

# 前端
npx jest
```

### 部署到服务器

参考 `部署说明.txt` 或 README.md 的部署章节。

---

## 五、关键设计决策

### API Key 的三层优先级

```
1. 管理后台网页配置（加密存 system_config 表） ← 最高优先
2. .env 文件 ANTHROPIC_API_KEY                 ← 兜底
3. 代码默认值                                    ← 无效
```

管理员在 `/admin/settings` 页面配置后立即生效，无需重启。

### 为什么前端是单文件 HTML

v7.4 版本是早期快速迭代的产物，将所有 JS/CSS/HTML 写在一个文件里。v2 版（`frontend/` 目录）是 Vite + TypeScript 重构版，但尚未完成。日常修改直接编辑 `mainboard_repair_system_v7.4_updated.html` 即可。

### 数据脱敏机制

```
data/internal/         ← 内部版（含真实飞书链接，gitignore，不提交）
data/public-backup/    ← 公开版备份（占位符链接）
data/*.js              ← 当前生效的数据文件

npm run setup-internal  → 切换到内部版
npm run restore-public  → 切换到公开版
```

---

## 六、常见问题排查

| 现象 | 可能原因 | 检查方法 |
|------|----------|----------|
| 前端 AI 诊断报错 | 健康检查 API 字段不匹配 | `curl localhost:8899/health` 确认 `ai.api_configured` |
| 仪表盘 500 | 数据库表缺少新列 | `alembic upgrade head` 运行迁移 |
| 注册报错 | 用户名含`.`或密码太简单 | 用户名只允许 `[a-zA-Z0-9_中文]`，密码需两类字符 |
| 非管理员能进后台 | 路由用了 `get_optional_user` | 检查 `admin.py` 路由是否用 `require_admin` |
| API Key 保存后不生效 | 数据库 system_config 表不存在 | `alembic upgrade head` |
| Windows 中文路径测试报错 | GBK编码问题 | 加环境变量 `PYTHONUTF8=1` |

---

## 七、环境变量速查

| 变量 | 必填 | 说明 |
|------|------|------|
| `ANTHROPIC_API_KEY` | 是 | AI 平台 API Key |
| `SECRET_KEY` | 是 | JWT 签名密钥，至少32字符 |
| `AI_PROVIDER` | 否 | deepseek/kimi-code/anthropic/kimi |
| `AI_MODEL` | 否 | 具体模型名 |
| `CORS_ORIGINS` | 生产必填 | 跨域来源，逗号分隔 |
| `DATABASE_URL` | 否 | PostgreSQL 连接串（默认 SQLite） |
| `LOG_FORMAT` | 否 | text/json，生产建议 json |
| `SENTRY_DSN` | 否 | 错误追踪 |
| `PORT` | 否 | 默认 8899 |
