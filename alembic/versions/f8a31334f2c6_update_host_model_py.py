"""update_host_model.py

Revision ID: f8a31334f2c6
Revises: 4224107043f1
Create Date: 2026-11-07 17:21:59.329788

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8a31334f2c6'
down_revision: Union[str, Sequence[str], None] = '4224107043f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновляем модель Host для интеграции с RedCheck."""
    # Удаляем старые колонки
    op.drop_column('host', 'ip_address')
    op.drop_column('host', 'hostname')
    
    # Добавляем новые колонки
    op.add_column('host', sa.Column('redcheck_id', sa.Integer(), nullable=True))
    op.add_column('host', sa.Column('guid', sa.String(length=36), nullable=True))
    op.add_column('host', sa.Column('uuid', sa.String(length=36), nullable=True))
    op.add_column('host', sa.Column('connection_address', sa.String(length=255), nullable=False))
    op.add_column('host', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('host', sa.Column('cpe', sa.String(length=255), nullable=True))
    op.add_column('host', sa.Column('is_dns', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('host', sa.Column('modification_date', sa.DateTime(), nullable=True))
    op.add_column('host', sa.Column('segment_id', sa.Integer(), nullable=True))
    op.add_column('host', sa.Column('is_deleted_in_redcheck', sa.Boolean(), nullable=False, server_default='false'))
    
    # Создаём уникальное ограничение
    op.create_unique_constraint('uq_host_group_redcheck', 'host', ['group_id', 'redcheck_id'])
    
    # Создаём индексы
    op.create_index('idx_host_redcheck_id', 'host', ['redcheck_id'])
    op.create_index('idx_host_connection_address', 'host', ['connection_address'])


def downgrade() -> None:
    """Откат изменений."""
    op.drop_index('idx_host_connection_address', 'host')
    op.drop_index('idx_host_redcheck_id', 'host')
    op.drop_constraint('uq_host_group_redcheck', 'host', type_='unique')
    
    op.drop_column('host', 'is_deleted_in_redcheck')
    op.drop_column('host', 'segment_id')
    op.drop_column('host', 'modification_date')
    op.drop_column('host', 'is_dns')
    op.drop_column('host', 'cpe')
    op.drop_column('host', 'description')
    op.drop_column('host', 'connection_address')
    op.drop_column('host', 'uuid')
    op.drop_column('host', 'guid')
    op.drop_column('host', 'redcheck_id')
    
    op.add_column('host', sa.Column('hostname', sa.String(length=100), nullable=True))
    op.add_column('host', sa.Column('ip_address', sa.String(length=45), nullable=False))
    # ### end Alembic commands ###