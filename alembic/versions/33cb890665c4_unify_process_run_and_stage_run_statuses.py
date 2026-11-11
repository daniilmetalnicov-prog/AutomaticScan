"""unify process_run and stage_run statuses

Revision ID: 33cb890665c4
Revises: d5eda8bdc9f6
Create Date: 2026-11-08 19:08:32.248227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '33cb890665c4'
down_revision: Union[str, Sequence[str], None] = 'd5eda8bdc9f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Унифицируем статусы ProcessRun и StageRun: PAUSED → HOLD."""
    
    # 1. Удаляем старый CHECK constraint
    op.drop_constraint('chk_process_run_status', 'process_run', type_='check')
    
    # 2. Обновляем существующие данные: PAUSED → HOLD
    op.execute("""
        UPDATE process_run 
        SET status = 'HOLD' 
        WHERE status = 'PAUSED'
    """)
    
    # 3. Создаём новый CHECK constraint с унифицированными статусами
    op.create_check_constraint(
        'chk_process_run_status',
        'process_run',
        "status IN ('IDLE', 'IN_PROGRESS', 'SUCCESS', 'SKIPPED', 'HOLD', 'CANCELLED', 'FAILED')"
    )


def downgrade() -> None:
    """Откат изменений: HOLD → PAUSED."""
    
    # 1. Удаляем новый CHECK constraint
    op.drop_constraint('chk_process_run_status', 'process_run', type_='check')
    
    # 2. Возвращаем старые данные: HOLD → PAUSED
    op.execute("""
        UPDATE process_run 
        SET status = 'PAUSED' 
        WHERE status = 'HOLD'
    """)
    
    # 3. Создаём старый CHECK constraint
    op.create_check_constraint(
        'chk_process_run_status',
        'process_run',
        "status IN ('IDLE', 'IN_PROGRESS', 'SUCCESS', 'FAILED', 'PAUSED', 'CANCELLED')"
    )
    # ### end Alembic commands ###
