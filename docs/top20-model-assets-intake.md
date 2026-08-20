# Top20 机型主板图 / 点位图接收入库说明

## 目标

制造中心提供 Top20 主板维修机型的主板图、点位图后，先进入机型资料库登记，再逐步关联故障、SOP 和可视化点位查询。

## 建议文件夹

```text
source-materials/manufacturing-center/top20-model-board-assets/
  <MODEL>/
    board-front.*
    board-back.*
    point-map-front.*
    point-map-back.*
    readme.md
```

示例：

```text
source-materials/manufacturing-center/top20-model-board-assets/BG6m/
  board-front.png
  board-back.png
  point-map-front.pdf
  point-map-back.pdf
  readme.md
```

## 接收资料时需要同步确认

- 机型名是否与售后系统 / L4 报告一致。
- 是否有别名、项目名或市场名。
- 图片对应主板正面还是反面。
- 点位图是否区分正反面。
- 是否存在主板版本差异。
- 是否适用于所有市场版本。
- 是否允许售后内部培训和海外 L4 使用。
- 是否有对应高频故障或典型维修案例。

## 登记位置

结构化登记写入：

```text
knowledge-base/model-board-assets.json
```

实际原始文件保存到：

```text
source-materials/manufacturing-center/top20-model-board-assets/
```

当前阶段不做图片上传后台；由 Codex 根据收到的文件路径入库。
