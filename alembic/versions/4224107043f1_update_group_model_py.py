"""update_group_model.py

Revision ID: 4224107043f1
Revises: 4ea101e91b15
Create Date: 2026-11-07 15:26:22.028094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4224107043f1'
down_revision: Union[str, Sequence[str], None] = '4ea101e91b15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляем поля для интеграции с RedCheck."""
    # Добавляем новые колонки
    op.add_column('group', sa.Column('redcheck_id', sa.Integer(), nullable=True))
    op.add_column('group', sa.Column('unique_id', sa.String(length=36), nullable=True))
    op.add_column('group', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('group', sa.Column('modification_date', sa.DateTime(), nullable=True))
    op.add_column('group', sa.Column('count_of_hosts', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('group', sa.Column('segment_id', sa.Integer(), nullable=True))
    op.add_column('group', sa.Column('is_deleted_in_redcheck', sa.Boolean(), nullable=False, server_default='false'))
    
    # Удаляем колонку subnet
    op.drop_column('group', 'subnet')
    
    # Создаём уникальные индексы
    op.create_unique_constraint('uq_group_redcheck_id', 'group', ['redcheck_id'])
    op.create_unique_constraint('uq_group_unique_id', 'group', ['unique_id'])


def downgrade() -> None:
    """Откат изменений."""
    op.drop_constraint('uq_group_unique_id', 'group', type_='unique')
    op.drop_constraint('uq_group_redcheck_id', 'group', type_='unique')
    
    op.drop_column('group', 'is_deleted_in_redcheck')
    op.drop_column('group', 'segment_id')
    op.drop_column('group', 'count_of_hosts')
    op.drop_column('group', 'modification_date')
    op.drop_column('group', 'description')
    op.drop_column('group', 'unique_id')
    op.drop_column('group', 'redcheck_id')
    
    op.add_column('group', sa.Column('subnet', sa.String(length=50), nullable=True))