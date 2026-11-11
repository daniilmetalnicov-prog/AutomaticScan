"""add_hold_data_to_stage_run

Revision ID: bca8f28801a7
Revises: 9ac9828ec6ed
Create Date: 2026-11-11 22:29:56.180377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bca8f28801a7'
down_revision: Union[str, Sequence[str], None] = '9ac9828ec6ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляем колонку hold_data (JSONB) в таблицу stage_run."""
    
    # Добавляем колонку hold_data для хранения контекста HOLD
    # Формат: {"phase": "REDCHECK"|"DB", "hosts_to_delete": [...]}
    op.add_column('stage_run', 
                  sa.Column('hold_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Откат изменений: удаляем колонку hold_data."""
    op.drop_column('stage_run', 'hold_data')
    # ### end Alembic commands ###
