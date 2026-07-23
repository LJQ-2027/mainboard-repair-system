# 智能主板维修系统 v8.0 AI版

基于 AI 大模型的智能主板维修辅助系统，支持 Anthropic Claude 和 DeepSeek 双平台。

## 视觉 QC 数据工作台

本机工作台入口：

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

这是内部视觉数据工作台，不是海外维修员入口。Milo 是实物照片的唯一来源，Codex 以数据管理员身份完成批量入库、配准修正、可见缺陷标注、Golden Sample 建立和训练数据导出。海外维修员不上传视觉照片，也不进入该工作台。

当前实现遵循服务器主导的 Web 架构：照片先在仓库外固化为受控来源包，依次通过来源审计、实物验收和 acceptance-qualified handoff，才由数据管理员传输到受控 FastAPI 服务；OpenCV 异步处理，自动失败回退人工四点配准，Golden Sample、候选决策和训练出口集中保存，浏览器只保留工作草稿并恢复已有服务器案例。权威设计见 `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`。

照片到达后不再手工复制或编写批次 JSON。数据管理员使用 `scripts/stage_visual_qc_source_package.py` 把 Milo 提供的临时附件逐字节保存到仓库外的内容寻址原片库，并同时生成 `VISUAL-QC-SOURCE-PACKAGE-V1` 来源回执和标准 intake manifest。工具不根据文件名或画面猜机型/板面，不修改来件，也不自动上传；`knowledge-base/visual-qc-proxy-inventory-v1.json` 固化所有已知点位图和手册代理图的审核哈希，缺失、替换或遗漏登记均锁死入库。`scripts/audit_visual_qc_source_library.py` 对完整包、当前代理撤销、对象完整性和孤立对象执行确定性只读巡检，不清理、不修复、不上传。低层 importer 只是 handoff 内部的可恢复传输实现，不能自行生成合格来源证明，也不是实物入库入口。完整命令见 `docs/visual-qc-capture-intake-spec-2026-07-20.md`。

受控照片包建立后，先用本地验收运行器生成质量证据、自动配准候选和逐图叠图：

```powershell
.\.venv\Scripts\python.exe scripts\run_visual_qc_physical_acceptance.py `
  --library-root D:\visual-qc-source-library `
  --package D:\visual-qc-source-library\packages\km4-physical-001\source-package.json `
  --output D:\visual-qc-acceptance\km4-physical-001
```

输出目录包含 `physical-registration-run.json`、`physical-registration-run.md` 和 `artifacts/*.registration-overlay.png`。`VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1` 只区分重拍、人工四点配准和自动候选待确认；不上传、不批准配准、不判断缺陷，也不允许据此宣称实物配准精度。原图与点位图之间没有测量真值时，叠图只能作为人工检查证据。

验收报告不能直接替代审核，也不能绕过后继续调用通用 importer。先执行验收合格交接器的干跑：

```powershell
.\.venv\Scripts\python.exe scripts\handoff_visual_qc_physical_package.py `
  D:\visual-qc-source-library\packages\km4-physical-001\source-package.json `
  D:\visual-qc-acceptance\km4-physical-001\physical-registration-run.json `
  --library-root D:\visual-qc-source-library `
  --handoff-root D:\visual-qc-handoffs\km4-physical-001 `
  --dry-run
```

干跑会重新核对来源包、归档 intake、验收报告、原图和逐图叠图，并生成 `VISUAL-QC-PHYSICAL-HANDOFF-V1`。存在重拍、处理错误、哈希漂移或叠图损坏时整包阻断；`automatic_candidate_review_required` 和 `manual_registration_required` 只表示可以进入服务器继续处理，不表示配准已确认。确认干跑回执后，使用同一命令移除 `--dry-run`，增加现有 `--api-base`、`--credential-file` 和可选 `--wait` 参数完成可恢复传输。交接回执同时保存来源包、归档 intake 和验收报告的原始字节哈希；恢复已有服务器任务时会核对 job/case 身份且不会重复上传。随后仍必须在内部工作台完成配准审核。

唯一操作顺序为：`stage -> source audit -> physical acceptance -> acceptance-qualified handoff dry-run -> controlled transfer -> server registration review`。Milo 仍是实物照片的唯一来源，Codex 仍是唯一数据操作员，海外维修员没有照片上传入口。

当前本地 HEAD 的数据管理员工作台支持服务器案例目录、原图恢复、任务轮询、自动候选叠图确认、人工四点回退、Golden Sample、差异热图和候选确认/驳回/暂缓；新实物案例只能由验收合格交接命令创建，浏览器没有直接上传入口。服务器侧包含批次与案例溯源、采集身份防污染、确定性合成透视、ORB/AKAZE 特征、RANSAC 单应性、结构化失败原因、持久化人工结论、磁盘压力健康状态和受控留存清理。

生产仍为 `f278061`，地址是 `https://cccsat.top/mb-repair-beta/`。该生产版本早于 qualified handoff、List V2、Detail V3 和浏览器上传移除，不能作为当前本地 HEAD 契约的验证环境，也不能接收 qualified handoff。只有单独批准并完成部署与迁移验证后，生产才切换到本地 HEAD 口径。操作与数据边界见 `docs/visual-qc-capture-intake-spec-2026-07-20.md`、`docs/visual-qc-workbench-2026-07-17.md` 和 `docs/visual-qc-server-api-2026-07-20.md`。

受控 beta 路由使用 Nginx Basic Auth，网关注入用户和权限，QC API 的 3020 端口只绑定回环地址。后端暂时沿用 `reviewer` 作为“数据管理员”权限的兼容值，不表示存在第二个人工审核角色；以后可在不改变业务数据契约的情况下替换为公司 SSO/OIDC。部署与回滚步骤见 `docs/beta-deployment.md`。

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
- **当前后端实现**：`visual_qc_server.py` 已提供验收合格交接接收、SQLite任务恢复、图像质量证据、自动配准候选与人工四点回退；本地运行和部署边界见 `docs/visual-qc-server-api-2026-07-20.md`
- **当前数据闭环**：Milo 提供照片；Codex 依次完成来源包固化、只读审计、离线质量/配准预检和验收合格交接，再在内部工作台完成配准、最终人工 QC、Golden Sample 版本化、差异候选决策和标注
- **当前训练出口**：数据管理员可获取仅含训练合格实拍案例的 `VISUAL-QC-TRAINING-MANIFEST-V1`、对应原图和确定性 `VISUAL-QC-COCO-V1`；`VISUAL-QC-DATASET-BUNDLE-V1` 封装清单、COCO、索引和原图，`VISUAL-QC-DATASET-AUDIT-V1` 解释每个案例被排除的首要门禁原因
- **当前浏览器接入**：内部视觉数据工作台只检索和恢复受控交接产生的服务器案例，并处理任务状态、自动候选确认、四点回退、Golden Sample、差异热图和逐候选人工决策；浏览器不创建实物服务器案例，海外维修员界面隐藏并由 API 拒绝所有照片入库和数据集工具
- **当前案例契约**：本地历史基线保留 `VISUAL-QC-CASE-V1`；接入服务器的新案例使用 `VISUAL-QC-CASE-V2`，机器可读定义见 `knowledge-base/visual-qc-case-v2-schema.json`
- **AI 平台**：Anthropic Claude / DeepSeek
- **通信协议**：SSE (Server-Sent Events) 流式传输

## License

MIT
