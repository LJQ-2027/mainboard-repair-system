# 智能主板维修系统 v9.0 团队版

基于 AI 大模型的智能主板维修辅助系统，支持 Kimi / Anthropic Claude / DeepSeek 多平台，提供多用户诊断、知识库管理、历史会话与数据统计能力。

## 功能特性

- 🤖 **AI 智能诊断**：通过大语言模型辅助分析主板故障
- 🔌 **多平台支持**：自动识别 API Key 类型，兼容 Kimi Code / Anthropic Claude / DeepSeek
- 📸 **原理图分析**：支持上传原理图截图进行视觉分析（需 Kimi Code / Claude API）
- 💬 **流式对话**：实时 SSE 流式输出，交互体验流畅
- 👥 **多用户系统**：支持注册登录、诊断记录与会话历史保存
- 📊 **管理后台**：`/admin` 数据统计看板、知识库与项目资料管理
- 🔒 **安全加固**：JWT 密钥强制校验、CORS 白名单、上传文件类型/大小限制、安全响应头部

## 项目结构

```
├── backend/                              # FastAPI 后端服务
│   ├── app/
│   │   ├── main.py                       # FastAPI 应用入口
│   │   ├── routers/                      # 路由（auth, chat, admin, health）
│   │   ├── services/                     # 业务逻辑（AI 代理、认证、聊天）
│   │   ├── models/                       # SQLAlchemy 数据模型
│   │   ├── middleware/                   # 安全头部、请求日志
│   │   ├── schemas/                      # Pydantic 请求/响应模型
│   │   └── config.py                     # 配置加载（Pydantic Settings）
│   ├── tests/                            # pytest 测试套件
│   ├── data/                             # SQLite 数据库、日志
│   └── requirements.txt                  # Python 依赖
├── frontend/                             # Vite + TypeScript 新版前端（开发中）
│   ├── src/                              # 源码
│   └── dist/                             # 构建产物，挂载在 /v2/
├── mainboard_repair_system_v7.4_updated.html  # 当前生产前端页面（挂载在 /）
├── data/                                 # 前端数据文件（JS 知识库）
│   ├── *.js                              # 当前生效的数据文件
│   ├── internal/                         # 内部版数据（含真实链接，不提交 Git）
│   └── public-backup/                    # 公开版备份
├── js/                                   # 前端共享 JS（SSE 解析器、marked 等）
├── tests/                                # Jest 测试（js/sseParser.js）
├── scripts/                              # 运维脚本
│   └── setup-internal.js                 # 一键恢复内部版数据链接
├── legacy/                               # 废弃代码（v8.x 旧代理，仅历史参考）
├── docs/                                 # 产品愿景、部署与安全边界文档
├── .env.example                          # 环境变量模板
├── docker-compose.yml                    # Docker 部署
├── Dockerfile                            # Docker 镜像
└── 启动AI服务.bat                         # Windows 一键启动脚本
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+（仅前端开发需要）

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入以下必填项：

```bash
# AI 平台 API Key（必填）
ANTHROPIC_API_KEY=sk-your-api-key-here

# JWT 签名密钥（必填，至少 32 字符，不可与 API Key 相同）
SECRET_KEY=$(openssl rand -base64 48)

# CORS 来源（生产环境必须指定具体域名）
CORS_ORIGINS=http://localhost:3000
```

### 2. 安装依赖并启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

### 3. 访问

打开浏览器访问 http://localhost:8899/

### Windows 一键启动

双击运行 `启动AI服务.bat`

## 技术架构

- **前端**：单 HTML 页面 + data/ JS 数据（新版 Vite 前端挂载在 `/v2/`）
- **后端**：FastAPI（端口 8899）
- **数据库**：SQLite（`backend/data/mainboard.db`）
- **AI 平台**：Kimi Code / Anthropic Claude / DeepSeek
- **通信协议**：SSE 流式传输

## 内部版部署

```bash
npm run setup-internal
```

该命令会将 `data/internal/` 中的内部版数据（含真实飞书链接）复制到 `data/` 根目录，原根目录文件自动备份到 `data/public-backup/`。

详细说明请查看 [`data/README.md`](data/README.md)。

## 测试

```bash
# 后端测试
cd backend
python -m pytest tests/ -v

# 前端 JS 测试（仓库根目录）
npx jest
```

## License

MIT
