# 售后场景知识库结构设计

## 1. 设计目标

售后场景知识库不是简单保存文件链接，而是把海外主板维修中会被反复使用的资料、经验、案例和诊断路径沉淀成结构化内容。

第一阶段目标：

- 让海外本地维修员可以按机型、故障现象和资料入口查到可执行信息；
- 让中方技术人员可以把经验沉淀成案例、故障知识和 SOP；
- 让技术支持可以基于统一结构组织培训、复盘和资料补齐；
- 为后续交互式 SOP、可视化点位图、AI 辅助和软硬件检测封装建立标准数据基础。

当前阶段不追求全量覆盖，先追求结构稳定、字段清楚、可逐步填充。

## 2. 总体结构

正式知识库建议由 6 个核心库和 2 个支撑库组成：

1. 机型资料库
2. 故障知识库
3. 器件与点位库
4. 诊断 SOP 库
5. 维修案例库
6. 维修边界库
7. 培训资料库
8. 缺口与需求库

核心关系：

```text
机型资料库
  -> 关联器件与点位库
  -> 关联故障知识库
  -> 关联诊断 SOP 库
  -> 关联维修案例库
  -> 关联培训资料库

故障知识库
  -> 关联推荐检查模块
  -> 关联推荐检查点位
  -> 关联诊断 SOP
  -> 关联维修案例
  -> 关联维修边界

维修案例库
  -> 反哺故障知识
  -> 反哺诊断 SOP
  -> 生成资料缺口和需求
```

## 3. 机型资料库

### 用途

记录每个项目/机型的主板资料状态，是用户按机型进入知识库的主入口。

### 关键字段

| 字段 | 说明 |
|---|---|
| model_id | 机型或项目代号，例如 X6878 |
| model_name | 项目名称或主板名称 |
| board_version | 主板版本 |
| platform | 平台，例如 MTK、展锐 |
| product_type | 智能机、功能机、平板等 |
| region_scope | 适用国家或区域 |
| schematic | 原理图资料 |
| boardview_or_layout | 位号图、BoardView 或 Layout 资料 |
| bom | BOM 或物料清单 |
| repair_guide | 维修指导书 |
| training_materials | 关联培训资料 |
| related_faults | 关联故障类型 |
| related_cases | 关联维修案例 |
| missing_items | 当前缺失资料 |
| updated_at | 更新时间 |

### 当前 demo 对应数据

当前 [project-database.js](../data/project-database.js) 已包含部分机型资料入口，可迁移到该库。

已有字段包括：

- `name`
- `version`
- `schematicUrl`
- `schematicName`
- `layoutUrl`
- `layoutName`
- `bomUrl`
- `bomName`
- `sopUrl`
- `sopName`

缺失字段包括：

- 平台
- 产品类型
- 国家/区域适用范围
- 关联故障
- 关联案例
- 缺失资料清单

## 4. 故障知识库

### 用途

记录售后现场看到的故障现象、常见原因、排查方向和关联资料，是按故障进入知识库的主入口。

### 关键字段

| 字段 | 说明 |
|---|---|
| fault_id | 故障编号 |
| fault_name | 故障名称，例如不开机、不充电 |
| aliases | 别名、关键词、现场常见描述 |
| applicable_models | 适用机型 |
| symptom_description | 现象描述 |
| common_causes | 常见原因 |
| recommended_modules | 推荐检查模块 |
| recommended_components | 推荐检查器件 |
| recommended_test_points | 推荐测试点 |
| initial_checks | 初步判断方法 |
| required_tools | 所需工具 |
| local_repair_actions | 可本地处理动作 |
| escalation_conditions | 需要升级中方技术人员的条件 |
| board_replacement_conditions | 建议换板条件 |
| related_sops | 关联 SOP |
| related_cases | 关联案例 |

### 当前 demo 对应数据

当前可由两份数据合并迁移：

- [diagnosis-rules.js](../data/diagnosis-rules.js)：偏“故障现象 -> 推荐器件/点位/概率/案例数”。
- [phenomena-search-index.js](../data/phenomena-search-index.js)：偏“维修报表现象关键词 -> Top 器件聚合”。

当前已有字段包括：

- 故障名称或现象关键词
- 推荐位号
- 器件类型
- 概率
- 案例数
- 故障类型
- 维修方法

缺失字段包括：

- 初步判断方法
- 所需工具
- 适用机型
- 升级条件
- 换板条件
- 关联 SOP

## 5. 器件与点位库

### 用途

记录机型下的关键器件、测试点、模块归属和故障关联，是后续可视化点位图和 AI 准确使用真实位号的基础。

### 关键字段

| 字段 | 说明 |
|---|---|
| component_id | 器件或测试点编号 |
| model_id | 所属机型 |
| module | 功能模块，例如电源、充电、射频 |
| designator | 位号，例如 U3901 |
| name | 器件名称 |
| type | 器件类型，例如 IC、电容、连接器、测试点 |
| part_number | 型号或规格 |
| board_side | 主板正面/反面 |
| board_area | 主板区域描述 |
| related_faults | 关联故障 |
| normal_voltage | 正常电压范围 |
| normal_resistance | 正常阻值范围 |
| normal_current | 正常电流范围 |
| required_tool | 检测工具 |
| repair_action | 常见维修动作 |
| notes | 备注 |

### 当前 demo 对应数据

当前 [component-map.js](../data/component-map.js) 已包含项目器件位号映射。

已有字段包括：

- 项目型号
- 功能模块
- 位号
- 器件名称
- 型号

缺失字段包括：

- 器件类型
- 主板位置
- 关联故障
- 正常电压/阻值/电流范围
- 检测工具
- 维修动作

## 6. 诊断 SOP 库

### 用途

记录标准诊断流程，是后续“交互式诊断 SOP”的核心。每条 SOP 应该能回答：什么时候用、测哪里、正常是什么、异常后下一步做什么。

### 关键字段

| 字段 | 说明 |
|---|---|
| sop_id | SOP 编号 |
| title | SOP 标题 |
| applicable_models | 适用机型 |
| applicable_faults | 适用故障 |
| prerequisites | 前置条件 |
| required_tools | 所需工具 |
| steps | 步骤列表 |
| post_repair_validation | 修后验证项目 |
| version | 版本 |
| updated_at | 更新时间 |

### SOP step 字段

| 字段 | 说明 |
|---|---|
| step_no | 步骤编号 |
| action | 操作说明 |
| target_component | 目标器件 |
| test_point | 测试点 |
| expected_value | 正常范围 |
| abnormal_condition | 异常判断 |
| next_if_normal | 正常时下一步 |
| next_if_abnormal | 异常时下一步 |
| record_required | 是否需要记录数据 |
| photo_required | 是否需要拍照 |
| repair_action | 可执行维修动作 |
| escalation_condition | 升级条件 |

### 当前 demo 对应数据

当前系统还没有真正的 SOP 数据模型。`project-database.js` 里只有维修指导书链接，`hardware-knowledge-base.js` 里有排查步骤描述，但还不是可执行的步骤树。

第一阶段应优先把 5-10 条高频故障流程转成 SOP 模板数据。

## 7. 维修案例库

### 用途

沉淀中方技术人员、L4 和海外本地维修员的真实案例，并反哺故障知识和 SOP。

### 关键字段

| 字段 | 说明 |
|---|---|
| case_id | 案例编号 |
| country_or_region | 国家或区域 |
| model_id | 机型 |
| board_version | 主板版本 |
| fault_name | 故障现象 |
| user_description | 用户或现场描述 |
| initial_test_result | 初测结果 |
| measured_data | 电压、阻值、电流等测试数据 |
| attachments | 图片、视频、Log |
| diagnosis_process | 定位过程 |
| failed_component | 损坏器件 |
| repair_action | 维修动作 |
| validation_result | 修后验证结果 |
| repeat_repair | 是否二返 |
| reusable_summary | 可复用经验总结 |
| can_convert_to_sop | 是否可转 SOP |
| created_at | 创建时间 |

### 当前 demo 对应数据

当前没有逐条案例库。`diagnosis-rules.js` 和 `phenomena-search-index.js` 中的 `case_count` 是聚合统计，不是完整维修案例。

第一阶段需要补一批真实样板案例，建议先从中方技术人员已经反复处理过的故障开始。

## 8. 维修边界库

### 用途

明确哪些问题海外本地可处理，哪些交给中方技术人员，哪些建议换板，避免把复杂高风险维修误下放。

### 关键字段

| 字段 | 说明 |
|---|---|
| boundary_id | 边界编号 |
| model_id | 适用机型 |
| fault_name | 适用故障 |
| local_repair_scope | 海外本地可处理范围 |
| expert_repair_scope | 中方技术人员处理范围 |
| board_replacement_condition | 建议换板条件 |
| forbidden_actions | 不建议执行的维修动作 |
| required_skill_level | 所需技能等级 |
| required_tools | 所需工具 |
| notes | 说明 |

### 当前 demo 对应数据

当前系统没有独立维修边界库。部分边界信息散落在专业诊断文字里，需要后续结构化。

## 9. 培训资料库

### 用途

管理 L4 和海外本地维修员学习材料，把培训内容和机型、故障、工具、SOP 关联起来。

### 关键字段

| 字段 | 说明 |
|---|---|
| training_id | 培训资料编号 |
| title | 培训主题 |
| target_role | 适用对象，例如海外维修员、L4、中方技术人员 |
| related_models | 关联机型 |
| related_faults | 关联故障 |
| required_tools | 所需工具 |
| material_link | 资料链接 |
| practice_board | 练习样板 |
| assessment_standard | 考核标准 |
| updated_at | 更新时间 |

### 当前 demo 对应数据

当前 `project-database.js` 中的 `sopUrl/sopName` 能部分承接维修指导书，但还没有培训资料库。

## 10. 缺口与需求库

### 用途

记录当前知识库还缺什么，方便后续向制造中心、技术支持或中方技术人员持续补齐。

### 关键字段

| 字段 | 说明 |
|---|---|
| request_id | 需求编号 |
| related_model | 关联机型 |
| related_fault | 关联故障 |
| gap_type | 缺口类型，例如原理图、点位图、SOP、测试点、正常值、案例 |
| description | 缺口描述 |
| provider | 需要谁提供 |
| priority | 优先级 |
| status | 状态，例如待确认、已请求、已收到、已转化、暂不可提供 |
| next_action | 下一步动作 |
| updated_at | 更新时间 |

### 当前 demo 对应数据

当前没有独立缺口库。页面中的“暂无资料”可以转化为缺口项，但还没有自动生成机制。

## 11. 第一阶段最小必填字段

为了让知识库尽快可用，第一阶段每条知识不需要填满所有字段，但至少要有以下字段：

| 字段 | 说明 |
|---|---|
| applicable_model | 适用机型 |
| fault_name | 故障现象 |
| recommended_module_or_point | 推荐检查模块或点位 |
| repair_boundary | 可处理/需升级/建议换板边界 |
| source_note | 资料来源说明 |

第一阶段的质量标准不是“资料很全”，而是每条资料都能回答：

```text
它适用于什么机型和故障？
它能指导维修员检查什么？
它不能指导什么？
遇到边界情况应该交给谁处理？
后续还缺什么资料？
```

## 12. 现有 demo 数据迁移建议

| 当前文件 | 迁移目标 | 说明 |
|---|---|---|
| project-database.js | 机型资料库 | 作为机型资料入口，补平台、区域、缺失资料、关联故障 |
| component-map.js | 器件与点位库 | 作为位号基础数据，补器件类型、位置、正常值、关联故障 |
| diagnosis-rules.js | 故障知识库 / 维修案例库聚合 | 保留推荐点位和统计信息，但需要补真实案例明细 |
| phenomena-search-index.js | 故障知识库 | 作为故障关键词和现象索引，后续合并别名 |
| hardware-knowledge-base.js | 故障知识库 / SOP 库 | 先作为专业诊断说明，后续拆成步骤化 SOP |
| log-knowledge-base.js | Log 分析知识库 | 可继续作为独立模块，后续关联故障和案例 |

## 13. 建议第一批填充范围

第一批不要追求全量，建议选择：

- 2-3 个重点机型；
- 5 类高频故障；
- 每类故障 3-5 条真实案例；
- 每个机型先补齐基础资料状态；
- 每类故障至少沉淀一条 SOP 草案；
- 每条 SOP 至少明确工具、检查点、正常/异常判断和升级条件。

建议优先选择：

1. 土耳其 / EE1 当前高频 L4 主板故障；
2. 中方技术人员已经反复处理过、经验成熟的问题；
3. 换板成本高但有机会维修的问题；
4. 已有培训材料或维修指导书覆盖的问题。
