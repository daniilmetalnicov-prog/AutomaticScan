"""add_report_tables

Revision ID: 9ac9828ec6ed
Revises: 2358907ebc9b
Create Date: 2026-11-09 21:24:29.587335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9ac9828ec6ed'
down_revision: Union[str, Sequence[str], None] = '2358907ebc9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаём таблицы для хранения отчётов и шаблонов."""
    
    # Таблица report (для этапа 4: Размещение отчётов)
    op.create_table('report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stage_run_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('network_path', sa.String(length=500), nullable=True),
        sa.Column('placed_at', sa.DateTime(), nullable=True),
        sa.Column('placement_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.PrimaryKeyConstraint('id', name='pk_report'),
        sa.ForeignKeyConstraint(['stage_run_id'], ['stage_run.id'], 
                                name='fk_report_stage_run', ondelete='CASCADE')
    )
    op.create_index('idx_report_stage_run', 'report', ['stage_run_id'])
    
    # Таблица report_template (шаблоны отчётов для этапа 5)
    op.create_table('report_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('format', sa.String(length=10), nullable=False),
        sa.Column('template_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name='pk_report_template')
    )
    
    # Таблица analytics_report (для этапа 5: Формирование аналитики)
    op.create_table('analytics_report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('process_run_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('report_type', sa.String(length=10), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('generation_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.PrimaryKeyConstraint('id', name='pk_analytics_report'),
        sa.ForeignKeyConstraint(['process_run_id'], ['process_run.id'], 
                                name='fk_analytics_report_process_run', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['report_template.id'], 
                                name='fk_analytics_report_template', ondelete='SET NULL')
    )
    op.create_index('idx_analytics_report_process_run', 'analytics_report', ['process_run_id'])


def downgrade() -> None:
    """Откат изменений: удаляем таблицы."""
    op.drop_index('idx_analytics_report_process_run', 'analytics_report')
    op.drop_table('analytics_report')
    op.drop_table('report_template')
    op.drop_index('idx_report_stage_run', 'report')
    op.drop_table('report')
    # ### end Alembic commands ###
