# 智能主板维修系统 v8.0 AI版

基于 AI 大模型的智能主板维修辅助系统，支持 Anthropic Claude 和 DeepSeek 双平台。

## 视觉 QC 数据工作台

本机工作台入口：

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

当前覆盖图片质量检查、四锚点配准、独立检查点、人工审核、矩形/多边形缺陷标注、编译器件 footprint 建议、IndexedDB 草稿，以及 `VISUAL-QC-CASE-V1` JSON 和标注预览图导出。数据边界和实物照片验收门禁见 `docs/visual-qc-workbench-2026-07-17.md`。

当前页面是本地数据工作台基线，不是正式部署架构。已确认的目标是服务器主导的Web平台：主板照片上传现有受控服务器，OpenCV异步处理，自动失败回退人工四点配准，Golden Sample和候选审核集中保存，浏览器仅保留弱网草稿。权威设计见 `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`。

## 功能特性

- 🤖 **AI 智能诊断**：通过大语言模型辅助分析主板故障
- 🔌 **多平台支持**：自动识别 API Key 类型，兼容 Anthropic Claude 和 DeepSeek
- 📸 **原理图分析**：支持上传原理图截图进行视觉分析（需 Claude API）
- 💬 **流式对话**：实时 SSE 流式输出，交互体验流畅
- 🔄 **协议转换**：自动将 Anthropic 格式请求转为 OpenAI 兼容格式
- 📚 **售后知识工作台**：接入 `knowledge-base/` 结构化资料，支持资料总览、MTK 信号查询、L4 报告洞察、资料缺口清单和 SOP 草案查看

## 项目结构

```
├── mainboard_repair_system_v7.4_updated.html  # 前端主页面
├── data/                                      # 项目资料、诊断规则、知识库和 log 规则
│   ├── project-database.js                    # 项目资料入口
│   ├── component-map.js                       # 项目器件位号映射
│   ├── hardware-knowledge-base.js             # 专业硬件诊断知识库
│   ├── diagnosis-rules.js                     # 历史案例诊断规则
│   ├── phenomena-search-index.js              # 故障现象搜索索引
│   └── log-knowledge-base.js                  # log 分析知识库
├── knowledge-base/                            # 第一阶段结构化售后知识条目
├── docs/                                      # 产品愿景、知识库结构、资料边界和协作说明
│   ├── knowledge-base-structure.md            # 售后场景知识库结构
│   ├── source-ingestion-template.md           # 资料入库登记模板
│   └── phase-1-knowledge-fill-plan.md         # 第一阶段知识库填充计划
├── ai_proxy_server.py                          # AI 代理服务器（Python）
├── 启动AI服务.bat                               # Windows 启动脚本
├── .env.example                                # 环境变量模板
└── README.md
```

## 当前阶段

项目当前优先建设第一阶段知识地基。AI 功能保留为辅助入口，但现阶段重点是把制造中心、技术支持和 L4 维修报告中的资料沉淀为可查、可看、可继续补全的知识库。

Phase 1A 已在前端增加：

- 诊断工作台：输入机型、故障、信号或故障代码后，自动聚合相关资料入口。
- 完整度仪表盘：汇总机型和故障包资料完整度，提示优先补齐事项。
- 资料总览：查看已入库资料来源、处理状态和目标知识库。
- 机型资料库：承接 Top20 主板图、点位图和机型级资料槽位，并显示资料完整度、缺口和机型详情。
- 故障包：按不开机、无服务、不充电、重启/卡 Logo、漏电流等高频故障组织资料建设。
- 案例回流模板：规范真实维修案例的字段、证据和审核状态。
- 交互式 SOP：把漏电流/待机电流异常 SOP 草案拆成可点击步骤树原型。
- MTK 信号查询：按模块、信号名、功能说明和参考值检索 MTK 信号条目。
- L4 报告洞察：查看脱敏维修报告中的高频机型、故障现象、故障归因和维修动作。
- 资料缺口清单：跟进后续需要向技术支持、制造中心和中方技术人员索要的资料。
- SOP 草案：展示待工程确认的 SOP 草案和 MTK 手册待转译入口。

## 快速开始

### 1. 环境要求

- Python 3.8+
- Anthropic API Key 或 DeepSeek API Key

### 2. 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# ANTHROPIC_API_KEY=sk-ant-api03-your-key-here  (Anthropic)
# 或
# ANTHROPIC_API_KEY=sk-your-deepseek-key-here   (DeepSeek)
```

### 3. 启动

**Windows:**
双击运行 `启动AI服务.bat`

**macOS/Linux:**
```bash
python ai_proxy_server.py
```

### 4. 访问

打开浏览器，访问前端页面 `mainboard_repair_system_v7.4_updated.html`，确保代理服务器在 `http://localhost:8899` 运行。

## 技术架构

- **前端**：纯 HTML/CSS/JS 页面，核心数据拆分到 `data/` 目录
- **当前后端**：Python HTTP Server 代理（端口 8899）
- **目标后端**：同域FastAPI服务、持久化QC任务、受控图片存储和CPU OpenCV Worker
- **AI 平台**：Anthropic Claude / DeepSeek
- **通信协议**：SSE (Server-Sent Events) 流式传输

## License

MIT
