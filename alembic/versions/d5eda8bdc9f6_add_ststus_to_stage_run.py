"""add ststus to stage_run

Revision ID: d5eda8bdc9f6
Revises: f88857da1553
Create Date: 2026-11-08 18:46:00.170487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd5eda8bdc9f6'
down_revision: Union[str, Sequence[str], None] = 'f88857da1553'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляем колонку status в таблицу stage_run."""
    
    # 1. Добавляем колонку status (nullable=True, чтобы заполнить существующие записи)
    op.add_column('stage_run', sa.Column('status', sa.String(length=30), nullable=True))
    
    # 2. Заполняем существующие записи значением по умолчанию
    # Для этапов, которые уже были созданы, устанавливаем статус в зависимости от gate_decision
    op.execute("""
        UPDATE stage_run 
        SET status = CASE 
            WHEN gate_decision = 'ALLOW' THEN 'IN_PROGRESS'
            WHEN gate_decision = 'SKIP' THEN 'SKIPPED'
            WHEN gate_decision = 'HOLD' THEN 'HOLD'
            WHEN gate_decision = 'ABORT' THEN 'FAILED'
            ELSE 'IDLE'
        END
        WHERE status IS NULL
    """)
    
    # 3. Делаем колонку NOT NULL с значением по умолчанию
    op.alter_column('stage_run', 'status',
                    existing_type=sa.String(length=30),
                    nullable=False,
                    server_default='IDLE')
    
    # 4. Добавляем CHECK constraint для допустимых значений
    op.create_check_constraint(
        'chk_stage_run_status',
        'stage_run',
        "status IN ('IDLE', 'IN_PROGRESS', 'SUCCESS', 'SKIPPED', 'HOLD', 'CANCELLED', 'FAILED')"
    )


def downgrade() -> None:
    """Откат изменений: удаляем колонку status."""
    
    # Удаляем CHECK constraint
    op.drop_constraint('chk_stage_run_status', 'stage_run', type_='check')
    
    # Удаляем колонку
    op.drop_column('stage_run', 'status')
    # ### end Alembic commands ###
