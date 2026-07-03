#!/usr/bin/env node
/**
 * 一键恢复内部版数据链接
 *
 * 数据目录结构说明：
 *
 *   data/                  ← 当前生效的数据文件（前端通过 /data/*.js 读取）
 *   ├── *.js               ← 知识库、诊断规则、器件映射、项目资料等
 *   ├── project-cases.js   ← 项目案例库（仅存在于根目录，不在 internal/ 中）
 *   ├── internal/          ← 内部版数据（含真实飞书/内部链接，不提交 Git）
 *   └── public-backup/     ← 公开版备份（首次运行本脚本时自动创建）
 *
 * 执行流程：
 * 1. 读取 data/internal/ 中的 .js 文件
 * 2. 将 data/ 根目录中对应的 .js 文件备份到 public-backup/（仅首次）
 * 3. 将 internal/ 中的文件复制到 data/ 根目录（覆盖）
 *
 * 注意：project-cases.js 不会被覆盖，因为 internal/ 中不存在该文件。
 *
 * 安全提示：
 * - 首次运行会创建 public-backup/ 作为还原点
 * - 重复运行不会覆盖已有的备份文件
 * - 如需还原公开版，手动复制 public-backup/ → data/ 根目录
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const INTERNAL_DIR = path.join(DATA_DIR, 'internal');

function setupInternal() {
    if (!fs.existsSync(INTERNAL_DIR)) {
        console.error('错误：data/internal/ 目录不存在');
        console.error('请先从内部仓库或备份中恢复 internal 目录');
        process.exit(1);
    }

    const files = fs.readdirSync(INTERNAL_DIR).filter(f => f.endsWith('.js'));

    if (files.length === 0) {
        console.error('错误：data/internal/ 中没有 .js 文件');
        process.exit(1);
    }

    console.log(`发现 ${files.length} 个内部数据文件：`);

    for (const file of files) {
        const src = path.join(INTERNAL_DIR, file);
        const dest = path.join(DATA_DIR, file);

        // 备份公开版（如果不存在备份）
        const publicBackup = path.join(DATA_DIR, 'public-backup');
        if (!fs.existsSync(publicBackup)) {
            fs.mkdirSync(publicBackup, { recursive: true });
        }
        const backupFile = path.join(publicBackup, file);
        if (fs.existsSync(dest) && !fs.existsSync(backupFile)) {
            fs.copyFileSync(dest, backupFile);
        }

        // 复制内部版
        fs.copyFileSync(src, dest);

        // 统计链接数量
        const content = fs.readFileSync(dest, 'utf-8');
        const linkCount = (content.match(/https?:\/\//g) || []).length;
        console.log(`  ✅ ${file} (${linkCount} 个外部链接)`);
    }

    console.log('\n内部数据链接已恢复！');
    console.log('备份保存在 data/public-backup/');
    console.log('\n验证：');
    console.log('  grep -n "feishu" data/*.js');
}

setupInternal();
