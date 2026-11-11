"""add_process_run_id_to_process_log

Revision ID: 2358907ebc9b
Revises: 85ca21b16d16
Create Date: 2026-11-08 23:12:16.124452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2358907ebc9b'
down_revision: Union[str, Sequence[str], None] = '85ca21b16d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляем колонку process_run_id в таблицу process_log."""
    
    op.add_column('process_log', 
                  sa.Column('process_run_id', sa.Integer(), nullable=True))
    
    # Создаём внешний ключ
    op.create_foreign_key(
        'fk_process_log_process_run',
        'process_log', 'process_run',
        ['process_run_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Создаём индекс для ускорения запросов
    op.create_index('idx_process_log_process_run', 'process_log', ['process_run_id'])


def downgrade() -> None:
    """Откат изменений: удаляем колонку process_run_id."""
    op.drop_index('idx_process_log_process_run', 'process_log')
    op.drop_constraint('fk_process_log_process_run', 'process_log', type_='foreignkey')
    op.drop_column('process_log', 'process_run_id')
    # ### end Alembic commands ###
