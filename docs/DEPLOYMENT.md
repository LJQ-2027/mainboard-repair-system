# 部署指南

## 公开版 vs 内部版

本项目分为两个版本：

| | 公开版 (public) | 内部版 (internal) |
|---|---|---|
| **仓库** | GitHub 公开仓库 | 公司内部私有仓库/部署 |
| **数据链接** | 脱敏占位符 `[内部知识库链接]` | 真实飞书/内部知识库链接 |
| **API Key** | 用户自行配置 `.env` | 公司统一分配的 Key |
| **用途** | 开源协作、技术展示 | 海外售后现场使用 |

## 快速开始（公开版）

```bash
# 1. 克隆仓库
git clone https://github.com/LJQ-2027/mainboard-repair-system.git
cd mainboard-repair-system

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 Kimi / Anthropic / DeepSeek API Key

# 3. 启动后端代理
cd backend
pip install -r requirements.txt
python run.py

# 4. 启动前端（开发模式）
cd ../frontend
npm install
npm run dev

# 5. 浏览器访问 http://localhost:5173
```

## 内部版部署

### 方法一：一键恢复内部链接

```bash
npm run setup-internal
# 或
node scripts/setup-internal.js
```

这会从 `data/internal/` 复制带真实链接的数据文件到 `data/`。

### 方法二：手动替换

```bash
# 备份公开版数据
cp data/*.js data/public-backup/

# 复制内部版数据
cp data/internal/*.js data/

# 确认链接已恢复
grep -n "feishu" data/*.js
```

### 内部版 .env 配置

```bash
# 公司内部 API Key（由技术支持分配）
ANTHROPIC_API_KEY=sk-kimi-xxxxxxxx
AI_PROVIDER=kimi-code
AI_MODEL=kimi-k2-thinking
```

## 生产环境部署

### 数据库迁移

项目已配置 Alembic。首次部署或更新模型后，请执行：

```bash
cd backend
alembic upgrade head
```

创建新的模型迁移：

```bash
alembic revision --autogenerate -m "描述变更内容"
alembic upgrade head
```

### 数据库

项目默认使用 SQLite（`backend/data/mainboard.db`），适合开发和小规模试用。

#### 生产环境：PostgreSQL

1. 设置 `DATABASE_URL`：

```bash
DATABASE_URL=postgresql://user:password@host:5432/mainboard_repair
```

2. 安装 PostgreSQL 驱动（已包含在 requirements.txt）：

```bash
pip install psycopg2-binary
```

3. 执行迁移：

```bash
cd backend
alembic upgrade head
```

#### Docker Compose（含 PostgreSQL）

```bash
# 复制并编辑 .env
cp .env.example .env
# 填写 ANTHROPIC_API_KEY、SECRET_KEY 等必填项

# 启动服务（自动创建 PostgreSQL 并运行迁移）
docker-compose up -d
```

注意：docker-compose.yml 中 backend 服务默认等待 db healthy 后启动，但首次仍需手动进入容器执行 `alembic upgrade head`。

### 监控与日志

#### 日志格式

开发环境使用文本格式：

```bash
LOG_FORMAT=text
```

生产环境建议使用 JSON 格式，便于日志收集系统解析：

```bash
LOG_FORMAT=json
```

#### Prometheus 指标

应用默认暴露 `/metrics` 端点，包含：

- `http_requests_total`：HTTP 请求总数
- `http_request_duration_seconds`：HTTP 请求耗时
- `ai_calls_total`：AI 调用总数
- `ai_call_duration_seconds`：AI 调用耗时

在 `docker-compose.yml` 中可配置 Prometheus 抓取：

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

#### Sentry 错误追踪（可选）

配置 `SENTRY_DSN` 即可启用：

```bash
SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz
```

### 后端（FastAPI）

```bash
cd backend
pip install -r requirements.txt

# 开发模式
python run.py

# 生产模式（使用 Uvicorn）
uvicorn app.main:app --host 0.0.0.0 --port 8899 --workers 4
```

### 前端（Vite 构建）

```bash
cd frontend
npm install
npm run build

# 构建产物在 frontend/dist/ 目录
# 可使用任意静态文件服务器部署
npx serve dist
```

## 数据更新流程

### 更新知识库

1. 在 `data/internal/` 中修改 `.js` 文件
2. 运行 `npm run validate-data` 校验格式
3. 提交到内部仓库
4. 如需同步到公开版，替换链接为占位符后提交

### 备份用户数据

用户位号数据存储在浏览器 IndexedDB 中。导出方式：

```javascript
// 在浏览器控制台执行
(await import('./src/utils/storage.js')).exportAllData()
```

## 常见问题

**Q: 清浏览器缓存后数据会丢失吗？**
A: 不会。Phase 2 已迁移到 IndexedDB，不受"清除 Cookie"影响。但"清除网站数据"会删除 IndexedDB。

**Q: 可以同时运行旧版和新版吗？**
A: 可以。旧版 `legacy.html` 和新版 `frontend/` 共用同一个后端代理。

**Q: 如何回滚到旧版代理？**
A: `python ai_proxy_server.py`（标记为 @deprecated，保留兼容）
