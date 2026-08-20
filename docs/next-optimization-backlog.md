# 下一阶段优化 Backlog

## P0：Top20 图纸到位后的立即动作

- 将每个机型的主板正反面图、点位图保存到 `source-materials/manufacturing-center/top20-model-board-assets/<MODEL>/`。
- 更新 `knowledge-base/model-board-assets.json` 的 `assets` 路径。
- 将 `required_materials.board_images` 和 `required_materials.point_maps` 从 `missing` 更新为 `ready` 或 `partial`。
- 确认每张图对应的主板版本和适用范围。

## P1：机型详情页增强

- 增加图片预览区：正面主板图、反面主板图、正面点位图、反面点位图。
- 增加资料版本提示：图纸版本、来源、接收日期、是否工程确认。
- 增加“该机型待补资料”自动摘要。

## P2：故障包建设

- 先建设不开机、不充电、无服务/无网络、重启/卡 Logo、漏电流/待机电流异常五类故障包。
- 每个故障包关联适用机型、模块、点位、SOP、案例和维修边界。

## P3：SOP 步骤树

- 把 SOP 草案拆为机器可读步骤：测量动作、输入值、判断条件、下一步。
- 先用漏电流/待机电流异常作为样板。

## P4：案例回流

- 建立维修案例结构：机型、现象、测量值、维修动作、结果、返修情况、审核结论。
- 已验证案例反哺故障知识和 SOP。

## P5：AI/硬件预留

- 所有测试点都沉淀标准值和测量条件。
- 所有 SOP 步骤保留机器可读判断条件。
- 所有案例保留结构化结论，后续可用于 AI 导诊和检测治具数据解释。
