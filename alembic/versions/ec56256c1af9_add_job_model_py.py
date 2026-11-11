"""add_job_model.py

Revision ID: ec56256c1af9
Revises: f8a31334f2c6
Create Date: 2026-11-07 19:45:51.549715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ec56256c1af9'
down_revision: Union[str, Sequence[str], None] = 'f8a31334f2c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаём таблицу Job и промежуточные таблицы связей."""
    # Создаём таблицу job
    op.create_table('job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('redcheck_id', sa.Integer(), nullable=True),
        sa.Column('guid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scan_type', sa.Integer(), nullable=True),
        sa.Column('state', sa.Integer(), nullable=True),
        sa.Column('agent_type', sa.Integer(), nullable=True),
        sa.Column('creation_date', sa.DateTime(), nullable=True),
        sa.Column('modification_date', sa.DateTime(), nullable=True),
        sa.Column('hosts_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('groups_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_deleted_in_redcheck', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('redcheck_id')
    )
    
    # Создаём промежуточные таблицы связей
    op.create_table('job_host',
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('host_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('job_id', 'host_id')
    )
    
    op.create_table('job_group',
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('job_id', 'group_id')
    )
    
    # Создаём индексы
    op.create_index('idx_job_redcheck_id', 'job', ['redcheck_id'])
    op.create_index('idx_job_name', 'job', ['name'])
    op.create_index('idx_job_host_job_id', 'job_host', ['job_id'])
    op.create_index('idx_job_host_host_id', 'job_host', ['host_id'])
    op.create_index('idx_job_group_job_id', 'job_group', ['job_id'])
    op.create_index('idx_job_group_group_id', 'job_group', ['group_id'])


def downgrade() -> None:
    """Откат изменений."""
    op.drop_index('idx_job_group_group_id', 'job_group')
    op.drop_index('idx_job_group_job_id', 'job_group')
    op.drop_index('idx_job_host_host_id', 'job_host')
    op.drop_index('idx_job_host_job_id', 'job_host')
    op.drop_index('idx_job_name', 'job')
    op.drop_index('idx_job_redcheck_id', 'job')
    
    op.drop_table('job_group')
    op.drop_table('job_host')
    op.drop_table('job')
    # ### end Alembic commands ###
