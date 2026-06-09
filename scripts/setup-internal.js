#!/usr/bin/env node
/**
 * 一键恢复内部版数据链接
 * 从 data/internal/ 复制带真实链接的数据文件到 data/
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
