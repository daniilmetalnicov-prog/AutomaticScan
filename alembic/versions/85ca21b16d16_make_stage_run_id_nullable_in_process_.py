"""make stage_run_id nullable in process_log table

Revision ID: 85ca21b16d16
Revises: 84ff528b98c2
Create Date: 2026-11-08 19:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '85ca21b16d16'
down_revision: Union[str, None] = '84ff528b98c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Делаем колонку stage_run_id nullable в таблице process_log.
    
    Примечание: изменение уже применено вручную через SQL.
    Эта миграция служит для документирования изменения в истории Alembic.
    """
    # Изменение уже применено вручную. Оставляем пустую функцию для синхронизации.
    pass


def downgrade() -> None:
    """Откат изменений: делаем колонку stage_run_id NOT NULL."""
    
    # Удаляем NULL значения (если есть)
    op.execute("""
        UPDATE process_log 
        SET stage_run_id = 0 
        WHERE stage_run_id IS NULL
    """)
    
    # Делаем колонку NOT NULL
    op.alter_column('process_log', 'stage_run_id',
                    existing_type=sa.Integer(),
                    nullable=False)