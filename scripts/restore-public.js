#!/usr/bin/env node
/**
 * 一键恢复公开版数据（脱敏链接）
 *
 * 将 data/public-backup/ 中的公开版数据文件复制回 data/ 根目录，
 * 覆盖内部版数据（含真实飞书链接）。
 *
 * 用法：
 *   node scripts/restore-public.js
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const BACKUP_DIR = path.join(DATA_DIR, 'public-backup');

function restorePublic() {
    if (!fs.existsSync(BACKUP_DIR)) {
        console.error('错误：data/public-backup/ 目录不存在');
        console.error('没有可恢复的公开版备份');
        process.exit(1);
    }

    const files = fs.readdirSync(BACKUP_DIR).filter(f => f.endsWith('.js'));

    if (files.length === 0) {
        console.error('错误：data/public-backup/ 中没有 .js 文件');
        process.exit(1);
    }

    console.log(`恢复 ${files.length} 个公开版数据文件：`);

    for (const file of files) {
        const src = path.join(BACKUP_DIR, file);
        const dest = path.join(DATA_DIR, file);

        fs.copyFileSync(src, dest);

        // 验证脱敏
        const content = fs.readFileSync(dest, 'utf-8');
        const internalLinks = (content.match(/feishu|transsioner/gi) || []).length;
        const status = internalLinks === 0 ? '✅ 已脱敏' : `⚠️ 仍有 ${internalLinks} 个内部链接`;
        console.log(`  ${status}  ${file}`);
    }

    console.log('\n公开版数据已恢复！');
    console.log('如需切换回内部版，运行：npm run setup-internal');
}

restorePublic();
