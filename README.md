# 海外主板维修工作台

面向海外维修员的来源受控维修工作台，核心能力是交互式诊断 SOP、2.5D 主板模型、跨资料证据关联与视觉 QC 数据链路。通用大模型聊天、问答和自主诊断已经退役，不属于产品路线。

## 维修员内测入口

本地入口：

`http://127.0.0.1:51820/assets/technician-pilot/`

这是当前海外维修员内测的第一屏。维修员先选择已经确认的手机机型，再在同一个选择器中选择已知故障现象，或选择“不确定，先做初步排查”。入口使用八板目录解析 14 个机型别名，并通过严格 URL 契约进入现有跨资料维修工作台。

工作台只展示当前资料实际支持的能力：已审核 SOP 自动进入来源流程；KJ6/H897 按故障现象组织 13 条来源案例并提供板级或候选器件导航；没有审核步骤的板型只开放实物图、高清点位图、2.5D、器件和来源依据，并明确停止。案例候选不等于故障因果，系统不会补写电气参数、维修动作、缺陷标签或诊断结论。

经审核的可执行流程会建立一份本机维修会话：每次测量、分支选择、维修动作、复检和结束状态都会自动保存，刷新同一机型、主板和入口后可恢复；中途重置保留旧记录为已放弃，已完成记录不会被后续轮次覆盖。维修员可导出隐私最小化的 `TECHNICIAN-REPAIR-SESSION-V1` JSON。会话仅包装来源流程，不增加诊断结论，也不上传服务器或写回知识库。XK67J `source_boundary_only` 定位路径与 H897 案例导航仍是参考能力，不会伪装成正式维修会话。

内测反馈只记录“目标位置是否找到”和“资料是否足够继续”，保存在当前浏览器并由维修员手动导出 JSON。它与维修会话相互独立，不接收照片，不写入知识库，也不会自动成为维修事实。入口实现和验收记录见 `docs/technician-pilot-entry-2026-08-03.md`；维修会话实现记录见 `docs/technician-repair-session-2026-08-09.md`。

## 视觉 QC 数据工作台

本机工作台入口：

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

这是内部视觉数据工作台，不是海外维修员入口。Milo 是实物照片的唯一来源，Codex 以数据管理员身份完成批量入库、配准修正、可见缺陷标注、Golden Sample 建立和训练数据导出。海外维修员不上传视觉照片，也不进入该工作台。

当前实现遵循服务器主导的 Web 架构：照片先在仓库外固化为受控来源包，依次通过来源审计、实物验收和 acceptance-qualified handoff，才由数据管理员传输到受控 FastAPI 服务；OpenCV 异步处理，自动失败回退人工四点配准，Golden Sample、候选决策和训练出口集中保存，浏览器只保留工作草稿并恢复已有服务器案例。权威设计见 `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`。

照片到达后不再手工复制或编写批次 JSON。数据管理员使用 `scripts/stage_visual_qc_source_package.py` 把 Milo 提供的临时附件逐字节保存到仓库外的内容寻址原片库，并同时生成 `VISUAL-QC-SOURCE-PACKAGE-V1` 来源回执和标准 intake manifest。工具不根据文件名或画面猜机型/板面，不修改来件，也不自动上传；`knowledge-base/visual-qc-proxy-inventory-v1.json` 固化所有已知点位图和手册代理图的审核哈希，缺失、替换或遗漏登记均锁死入库。`scripts/audit_visual_qc_source_library.py` 对完整包、当前代理撤销、对象完整性和孤立对象执行确定性只读巡检，不清理、不修复、不上传。低层 importer 只是 handoff 内部的可恢复传输实现，不能自行生成合格来源证明，也不是实物入库入口。完整命令见 `docs/visual-qc-capture-intake-spec-2026-07-20.md`。

Milo 提供的真实维修案例使用独立的维修案例事实源。`VISUAL-QC-REPAIR-CASE-SOURCE-V1` 历史清单继续可读且不可变；当精确 `board_key` / `board_id` 和完整身份依据已具备、但来源机型名与目录机型名尚不能安全归一时，新修订使用 `VISUAL-QC-REPAIR-CASE-SOURCE-V2` 保存 `unresolved_alias`。Codex 先把案例照片固化为一个或多个来源包，再用 `scripts/stage_visual_qc_repair_case.py` 将明确的机型、板号、前后维修阶段、症状、发现、动作、结果和补充文件连接成不可覆盖的修订链。身份通过追加完整 revision 和 appended evidence 按允许的状态转换单调前进；只有 `conflict -> confirmed_alias` 强制新增 correction record；resolved identity 不可变。`completeness` 只表示当前上下文是否齐全，不表示描述正确、缺陷已确认、Golden 已批准或样本可训练。案例库不会自动写入视觉标注、QC 结论、Golden、COCO、训练清单、受治理数据包或服务器 API。

V3 `supporting_only` 用于只有维修过程补充照片、没有来源包链接的维修案例证据。数据管理员使用：

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_repair_case.py `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library `
  --repair-case-id case-003-bg6-f069 `
  --board-key bg6h-f069 `
  --case-record "C:\incoming\case-record-v3.json" `
  --supporting-file "repair-in-progress-photo=C:\incoming\IMG_5604.HEIC"
```

缺少 `--source-package` 仅对 V3 `supporting_only` 有效。`source_capture_stage` 保留来源原文，不是 Visual-QC stage。该路径不创建 derivative、registration、Golden、QC、annotation、training、API、server 或 production record。V1/V2 package-linked 行为保持不变。Milo 仍是唯一真实材料来源，Codex 仍在 owner-operated 边界内作为唯一数据操作员；这不是 technician upload。

首个 V2 实例已在仓库外受控库发布：`case-005-bg6-f069` revision 1，`board_key=bg6h-f069`，`board_id=BOARD-F069-MAIN-V1.2`，manifest SHA-256 `85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177`，schema 为 `VISUAL-QC-REPAIR-CASE-SOURCE-V2`，身份状态为 `unresolved_alias`，`model_identity_resolved=false`，完整度为 `symptom_linked`。来源报告机型 `TECNO/BG6`，目录机型为 `BG6H/BG6h`；在新增证据前不得强行归一。该事实源不是视觉诊断证据、不是缺陷确认证据、不是 Golden Sample 证据、不是训练标签证据、不是维修因果证据、不是现场精度证据。CASE005 本地发布当时未修改 `f278061` 生产服务器；后续能力部署也没有传输该本地证据或改变其证据边界。

案例材料的唯一顺序为：`stage source package(s) -> source audit -> stage repair case revision -> validate append-only case chain -> later physical acceptance on selected photo package`。Milo 只需提供原始材料和已知背景；Codex 负责稳定 ID、来源包角色、结构化转录和缺失字段报告。维修案例入库不包含组织审批，也不允许根据照片猜机型、板面、故障或维修结果。

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

生产已于 2026-08-03 升级到 `7ed316c07130ef1488037f537c5968c832e16668`，地址是 `https://cccsat.top/mb-repair-beta/`。该版本在既有受控 Visual-QC、证据链和共享组件视觉能力之上，部署了八板/14 机型的统一维修员入口、已知故障与未知坏点初步排查单一路径，以及 KJ6/H897 症状优先案例导航。升级从 `08d08cd38aaffc9b01d901dfe9ef7684a614abac` 执行不可变归档校验、一致 SQLite 备份和完整迁移/回滚演练；生产 P4 通过。操作与数据边界见 `docs/visual-qc-capture-intake-spec-2026-07-20.md`、`docs/visual-qc-workbench-2026-07-17.md` 和 `docs/visual-qc-server-api-2026-07-20.md`。

本地 HEAD 已增加 `VISUAL-QC-UPGRADE-PREFLIGHT-V1` 升级演练门禁和 `VISUAL-QC-DEPLOYMENT-MANIFEST-V1` 部署身份清单。`scripts/audit_visual_qc_upgrade.py` 只接受一致 SQLite 备份，在临时副本上验证受控对象、加法式迁移、Health/List/Detail/Dataset 契约、legacy 训练排除和旧版回读；源库与对象保持只读。真实部署会先将完整 40 位 commit、实际归档 SHA-256/字节数和归档内部运行时清单的 SHA-256 绑定为一个确定性清单，并上传到本次部署独有的只读暂存目录；本地清单只用于核对路径集合，Windows CRLF 不会替代 Git 归档中的真实字节身份。服务器在解包前拒绝重复 JSON 字段、身份不一致和危险 tar 成员，解包后拒绝符号链接、硬链接、特殊文件和运行时边界漂移，最后才停服备份和执行迁移演练。app/venv 只有在完整升级报告通过 JSON Schema、数据库快照和全部候选身份复核后才会切换。使用和证据边界见 `docs/visual-qc-upgrade-preflight-2026-07-23.md`。这些能力本身不代表已经升级生产。

受控 beta 路由使用 Nginx Basic Auth，网关注入用户和权限，QC API 的 3020 端口只绑定回环地址。后端暂时沿用 `reviewer` 作为“数据管理员”权限的兼容值，不表示存在第二个人工审核角色；以后可在不改变业务数据契约的情况下替换为公司 SSO/OIDC。部署与回滚步骤见 `docs/beta-deployment.md`。

## 功能特性

- **交互式诊断 SOP**：根据已审核来源和维修员测量结果推进确定性维修分支
- **可恢复维修会话**：在本机保存来源流程中的测量、选择、动作与复检，支持刷新恢复、新一轮留痕和隐私最小化导出
- **2.5D 主板模型**：支持板面浏览、器件选择、隔离查看与维修上下文联动
- **跨资料证据关联**：连接点位图、原理图、维修手册、器件身份与案例证据
- **视觉 QC 数据链路**：支持受控照片入库、OpenCV 配准、Golden Sample、差异候选、人工确认与训练数据出口
- 📚 **售后知识工作台**：接入 `knowledge-base/` 结构化资料，支持资料总览、MTK 信号查询、L4 报告洞察、资料缺口清单和 SOP 草案查看

历史 `/api/chat`、Anthropic/DeepSeek 适配和相关启动入口仅为未清理的遗留实现，必须保持关闭；不得配置、扩展、部署为产品能力或纳入验收。

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

项目当前围绕维修员实际路径建设知识地基、2.5D 模型、来源受控 SOP 和视觉 QC。通用大模型功能不再保留为辅助入口。

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
- 项目依赖见仓库现有 Python 环境与部署文档

### 2. 启动与访问

维修工作台和视觉 QC 服务按 `docs/beta-deployment.md` 与 `docs/visual-qc-server-api-2026-07-20.md` 启动。不要使用历史 AI 启动脚本，也不要配置 LLM API Key。

## 技术架构

- **前端**：纯 HTML/CSS/JS 页面，核心数据拆分到 `data/` 目录
- **当前后端**：Python HTTP Server 代理（端口 8899）
- **目标后端**：同域FastAPI服务、持久化QC任务、受控图片存储和CPU OpenCV Worker
- **当前后端实现**：`visual_qc_server.py` 已提供验收合格交接接收、SQLite任务恢复、图像质量证据、自动配准候选与人工四点回退；本地运行和部署边界见 `docs/visual-qc-server-api-2026-07-20.md`
- **当前数据闭环**：Milo 提供照片；Codex 依次完成来源包固化、只读审计、离线质量/配准预检和验收合格交接，再在内部工作台完成配准、最终人工 QC、Golden Sample 版本化、差异候选决策和标注
- **当前训练出口**：数据管理员可获取仅含训练合格实拍案例的 `VISUAL-QC-TRAINING-MANIFEST-V1`、对应原图和确定性 `VISUAL-QC-COCO-V1`；`VISUAL-QC-DATASET-BUNDLE-V1` 封装清单、COCO、索引和原图，`VISUAL-QC-DATASET-AUDIT-V1` 解释每个案例被排除的首要门禁原因
- **当前浏览器接入**：内部视觉数据工作台只检索和恢复受控交接产生的服务器案例，并处理任务状态、自动候选确认、四点回退、Golden Sample、差异热图和逐候选人工决策；浏览器不创建实物服务器案例，海外维修员界面隐藏并由 API 拒绝所有照片入库和数据集工具
- **当前案例契约**：本地历史基线保留 `VISUAL-QC-CASE-V1`；接入服务器的新案例使用 `VISUAL-QC-CASE-V2`，机器可读定义见 `knowledge-base/visual-qc-case-v2-schema.json`
- **视觉处理**：CPU OpenCV Worker 与后续专用视觉模型
- **数据协议**：版本化案例、配准、Golden Sample、候选与训练出口契约

## License

MIT

## 2026-07-29 当前补充：维修案例证据关联

The controlled library is the authoritative source of truth for each immutable
repair-evidence-link revision. The server stores only a read-only projection
that can be rebuilt by validating and replaying that exact library revision.
The contract enforces one photo per binding; one link revision may contain
separate bindings for separate photos.

Repair-evidence detail is exposed only through the administrator/reviewer
detail API. Technicians have no repair-evidence detail route. A binding records
an evidence association only and carries no annotation, QC, Golden Sample,
training-label, repair-causality, or repair-action authority.

CASE005 keeps the source-reported U4000 association as `possibly_related` and
`not_assessed`. It has no visual defect conclusion and does not establish that
U4000 caused the reported symptom or that any repair action is required.

The owner-operated chain is:

```text
repair case revision
-> export linkable physical evidence
-> stage repair evidence link revision
-> validate/replay
-> sync read-only projection
-> inspect in internal workbench
```

The CASE005 controlled-library publication and its local projection remain
local evidence only. The server capability was later deployed at
`08d08cd38aaffc9b01d901dfe9ef7684a614abac`, but that deployment did not
transfer the local CASE005 projection or turn it into a visual conclusion.
