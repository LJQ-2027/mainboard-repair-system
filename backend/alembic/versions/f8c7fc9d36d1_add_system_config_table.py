"""add_system_config_table

Revision ID: f8c7fc9d36d1
Revises: 8a3cad7595b8
Create Date: 2026-07-08 09:39:52.580548

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8c7fc9d36d1'
down_revision: Union[str, Sequence[str], None] = '8a3cad7595b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # system_config 表（兼容 init_db 已创建的情况）
    op.execute("CREATE TABLE IF NOT EXISTS system_config ("
               "id INTEGER PRIMARY KEY AUTOINCREMENT, "
               "key VARCHAR(100) NOT NULL, "
               "value TEXT NOT NULL, "
               "description VARCHAR(500), "
               "updated_at DATETIME)")

    # 索引（IF NOT EXISTS 兼容）
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_system_config_key ON system_config (key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_system_config_id ON system_config (id)")

    # diagnosis_records 新增 sop_session_id 列
    try:
        op.add_column('diagnosis_records', sa.Column('sop_session_id', sa.Integer(), nullable=True))
    except Exception:
        pass  # 列已存在（SQLite 不支持 IF NOT EXISTS 列）

    try:
        op.create_index(op.f('ix_diagnosis_records_sop_session_id'), 'diagnosis_records', ['sop_session_id'], unique=False)
    except Exception:
        pass

    try:
        op.create_foreign_key(None, 'diagnosis_records', 'diagnosis_sop_sessions', ['sop_session_id'], ['id'])
    except Exception:
        pass  # 外键可能已存在


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_constraint(None, 'diagnosis_records', type_='foreignkey')
    except Exception:
        pass
    op.drop_index(op.f('ix_diagnosis_records_sop_session_id'), table_name='diagnosis_records')
    op.drop_column('diagnosis_records', 'sop_session_id')
    op.drop_index(op.f('ix_system_config_key'), table_name='system_config')
    op.drop_index(op.f('ix_system_config_id'), table_name='system_config')
    op.drop_table('system_config')
