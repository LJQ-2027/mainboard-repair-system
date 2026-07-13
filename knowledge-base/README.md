# 售后场景知识库数据

本目录用于沉淀第一阶段结构化知识条目。

当前数据来源于技术支持、培训资料、中方技术人员经验和后续现场案例。第一阶段先用 JSON 文件维护，便于后续接入页面、搜索和 AI 上下文。

## 文件说明

- `source-records.json`：收到的原始资料登记表。
- `service-manual-library-2026-07-10.json`：大型 Service Manual 资料库的逐文件清单、SHA-256、重复映射、机型标签和可解析性检查。
- `vision-reference-gallery.json`：从优先机型 Service Manual 中提取的主板视觉候选页、嵌入图片、板号关联和人工复核结果。
- `vision-reference-review.json`：视觉参考图的人工选片、用途分类、参考强度和标准正反面照片缺口。
- `assets/vision-reference-gallery/`：七个重合机型、21 张已复核 Service Manual 参考图的本地浏览图库。
- `assets/vision-recognition-demo/`：基于上述参考图运行的浏览器端图像质量检查与七机型相似度检索 Demo。
- `km4-cross-source-registration.json`：KM4/F151 首批实体的归一化几何、代理照片配准、SCH证据、维修指导和2.5D视觉参数。
- `km4-point-map-geometry.json`：从KM4/F151第2面点位图红色工程层自动提取的匿名归一化结构区域，不伪造位号语义。
- `km4-board-compiled.json`：主板编译器直接解析KM4/F151位号图PDF的Form XObject、字体CMap、文字坐标和矢量矩形后生成的820个带位号候选实体。
- `assets/cross-source-registration/`：实体代理图、点位图和参数化2.5D模型共用 `component_id` 的跨资料联动工作台。
- `training-materials.json`：培训资料条目。
- `module-principles.json`：手机模块原理、关键链路和后续可转化为诊断说明的基础知识。
- `platform-repair-manuals.json`：制造中心提供的平台级主板维修通用手册摘要。
- `model-board-assets.json`：Top20 候选机型的主板图、点位图和机型级资料槽位登记。
- `mtk-signal-reference.json`：MTK 平台手册中抽取的信号名称、功能说明和测试参考值。
- `fault-knowledge.json`：故障现象、常见原因、初步判断方法和建议检测方向。
- `fault-packages.json`：高频主板故障包，用于组织 SOP、测试点、案例、点位图和维修边界建设。
- `repair-case-template.json`：主板维修案例回流模板，定义字段、证据清单和审核状态。
- `interactive-sop-prototypes.json`：交互式 SOP 步骤树原型，当前用于漏电流/待机电流异常草案。
- `sop-drafts.json`：从现有资料中抽取的诊断 SOP 草案，后续需由技术支持或制造中心确认。
- `model-repair-guidance-coverage.json`：机型维修步骤指导覆盖清单，记录每个机型基于现有资料生成了哪些 SOP。
- `repair-report-summaries.json`：L4 维修报告等明细数据的脱敏汇总，不保存 IMEI、序列号、技师姓名和原始工单明细。
- `repair-boundaries.json`：维修能力边界、试点门槛和流程要求。
- `gap-requests.json`：从资料中识别出的缺口和后续需要补齐的下钻资料。

## 入库原则

- 核心原始资料应保存到 `source-materials/`，同时沉淀结构化记录和前端可见状态。
- 一个源文件可以拆到多个知识库。
- 缺失的下钻资料先进入缺口清单，不阻塞当前资料入库。
- 后续页面读取数据时，应优先使用这里的结构化条目，而不是直接解析原始文件。
- 当前阶段不把维修边界作为 SOP 生成的前置条件，优先补齐步骤指导、测试点参考和修后验证。
