#!/bin/bash
# 数据库自动备份脚本
# 用法: ./scripts/backup-db.sh [backup_dir]
#
# 推荐通过 cron 定时执行:
#   0 2 * * * /path/to/scripts/backup-db.sh /path/to/backups >> /var/log/mainboard-backup.log 2>&1
#
# 特性:
#   - SQLite: 使用 .backup 在线备份（不会阻塞读写）
#   - PostgreSQL: 使用 pg_dump
#   - 保留最近 30 天的备份，自动清理旧文件

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${1:-$PROJECT_DIR/backend/data/backups}"
DB_PATH="$PROJECT_DIR/backend/data/mainboard.db"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ---------- SQLite 备份 ----------
if [ -f "$DB_PATH" ]; then
    BACKUP_FILE="$BACKUP_DIR/mainboard_${TIMESTAMP}.db"

    # 使用 sqlite3 .backup 命令进行在线热备份
    if command -v sqlite3 &>/dev/null; then
        sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SQLite backup: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    else
        # 回退：直接复制（SQLite WAL 模式下安全）
        cp "$DB_PATH" "$BACKUP_FILE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SQLite copy: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    fi

    # 压缩
    gzip -f "$BACKUP_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Compressed: ${BACKUP_FILE}.gz"

# ---------- PostgreSQL 备份 ----------
elif [ -n "${DATABASE_URL:-}" ]; then
    BACKUP_FILE="$BACKUP_DIR/mainboard_${TIMESTAMP}.sql"

    # 从 DATABASE_URL 解析连接参数
    # 格式: postgresql://user:password@host:port/dbname
    if command -v pg_dump &>/dev/null; then
        pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] PostgreSQL dump: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: pg_dump not found, cannot backup PostgreSQL"
        exit 1
    fi

    gzip -f "$BACKUP_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Compressed: ${BACKUP_FILE}.gz"

else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No database found at $DB_PATH and DATABASE_URL not set"
    exit 1
fi

# ---------- 清理过期备份 ----------
DELETED=$(find "$BACKUP_DIR" -name "mainboard_*.gz" -mtime +$RETENTION_DAYS -delete -print 2>/dev/null | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned $DELETED old backup(s) (>${RETENTION_DAYS} days)"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete. Total backups: $(ls "$BACKUP_DIR"/*.gz 2>/dev/null | wc -l)"
