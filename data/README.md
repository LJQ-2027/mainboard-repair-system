# data/ 目录说明

## 文件结构

```
data/
├── *.js                    # 当前生效的数据文件（前端通过 /data/*.js 读取）
│   ├── component-map.js
│   ├── diagnosis-rules.js
│   ├── hardware-knowledge-base.js
│   ├── log-knowledge-base.js
│   ├── phenomena-search-index.js
│   ├── project-cases.js    # 项目案例库（仅存在于根目录）
│   └── project-database.js
├── internal/               # 内部版数据（含真实飞书/内部链接，不提交 Git）
│   └── *.js               # 与根目录同名，但链接为真实值
└── public-backup/          # 公开版备份（运行 setup-internal 时自动创建）
    └── *.js
```

## 数据更新流程

### 内部版 → 生效数据

1. 在 `data/internal/` 中修改数据
2. 运行 `npm run setup-internal` 或 `node scripts/setup-internal.js`
3. 确认根目录数据已更新
4. 刷新前端页面查看效果

### 还原公开版

```bash
# 从备份还原
cp data/public-backup/*.js data/
```

## 注意事项

- `project-cases.js` 仅在根目录存在，不在 `internal/` 中，更新时请勿误删
- `internal/` 目录已在 `.gitignore` 中排除，不会提交到 Git
- 公开版数据中的敏感链接应使用占位符（如 `[内部知识库链接]`）
- 修改生效数据前建议先备份，避免误操作导致数据丢失
