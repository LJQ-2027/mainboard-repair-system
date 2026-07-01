# 售后场景知识库数据

本目录用于沉淀第一阶段结构化知识条目。

当前数据来源于技术支持、培训资料、中方技术人员经验和后续现场案例。第一阶段先用 JSON 文件维护，便于后续接入页面、搜索和 AI 上下文。

## 文件说明

- `source-records.json`：收到的原始资料登记表。
- `training-materials.json`：培训资料条目。
- `module-principles.json`：手机模块原理、关键链路和后续可转化为诊断说明的基础知识。
- `platform-repair-manuals.json`：制造中心提供的平台级主板维修通用手册摘要。
- `mtk-signal-reference.json`：MTK 平台手册中抽取的信号名称、功能说明和测试参考值。
- `fault-knowledge.json`：故障现象、常见原因、初步判断方法和建议检测方向。
- `sop-drafts.json`：从现有资料中抽取的诊断 SOP 草案，后续需由技术支持或制造中心确认。
- `repair-report-summaries.json`：L4 维修报告等明细数据的脱敏汇总，不保存 IMEI、序列号、技师姓名和原始工单明细。
- `repair-boundaries.json`：维修能力边界、试点门槛和流程要求。
- `gap-requests.json`：从资料中识别出的缺口和后续需要补齐的下钻资料。

## 入库原则

- 原始 Word、PDF、图片、视频暂不直接放入仓库，先沉淀结构化记录。
- 若 Milo 明确要求保存核心原始资料，可放入 `source-materials/`，并在来源登记中记录保存路径。
- 一个源文件可以拆到多个知识库。
- 缺失的下钻资料先进入缺口清单，不阻塞当前资料入库。
- 后续页面读取数据时，应优先使用这里的结构化条目，而不是直接解析原始文件。
