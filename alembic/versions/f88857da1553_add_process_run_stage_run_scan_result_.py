"""add process_run stage_run scan_result process_log audit_log

Revision ID: f88857da1553
Revises: ec56256c1af9
Create Date: 2026-11-07 21:46:11.232720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f88857da1553'
down_revision: Union[str, Sequence[str], None] = 'ec56256c1af9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Обновляем существующие таблицы: добавляем недостающие колонки, меняем типы."""
    
    # ============================================================
    # 1. ОБНОВЛЕНИЕ ТАБЛИЦЫ job: JSON → JSONB
    # ============================================================
    op.alter_column('job', 'hosts_data',
                    existing_type=sa.Text(),
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    existing_nullable=True)
    op.alter_column('job', 'groups_data',
                    existing_type=sa.Text(),
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    existing_nullable=True)
    
    # ============================================================
    # 2. ОБНОВЛЕНИЕ ТАБЛИЦЫ process_run: добавляем group_id и error_message
    # ============================================================
    op.add_column('process_run', sa.Column('group_id', sa.Integer(), nullable=True))
    op.add_column('process_run', sa.Column('error_message', sa.Text(), nullable=True))
    op.create_foreign_key('fk_process_run_group', 'process_run', 'group', 
                          ['group_id'], ['id'], ondelete='SET NULL')
    
    # ============================================================
    # 3. ОБНОВЛЕНИЕ ТАБЛИЦЫ stage_run: добавляем stage_output_status
    # ============================================================
    op.add_column('stage_run', sa.Column('stage_output_status', sa.String(length=50), nullable=True))
    
    # ============================================================
    # 4. ОБНОВЛЕНИЕ ТАБЛИЦЫ scan_result: переименование колонок + FK
    # ============================================================
    # Переименовываем camelCase → snake_case
    op.alter_column('scan_result', 'lowseverity_count',
                    new_column_name='low_severity_count')
    op.alter_column('scan_result', 'mediumseverity_count',
                    new_column_name='medium_severity_count')
    op.alter_column('scan_result', 'highseverity_count',
                    new_column_name='high_severity_count')
    op.alter_column('scan_result', 'criticalseverity_count',
                    new_column_name='critical_severity_count')
    
    # process_run_id уже есть в таблице (из SQL-скрипта), просто добавляем FK
    op.create_foreign_key('fk_scan_result_process_run', 'scan_result', 'process_run', 
                          ['process_run_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Откат изменений."""
    
    # Удаляем FK
    op.drop_constraint('fk_scan_result_process_run', 'scan_result', type_='foreignkey')
    op.drop_constraint('fk_process_run_group', 'process_run', type_='foreignkey')
    
    # Возвращаем старые имена колонок в scan_result
    op.alter_column('scan_result', 'low_severity_count',
                    new_column_name='lowseverity_count')
    op.alter_column('scan_result', 'medium_severity_count',
                    new_column_name='mediumseverity_count')
    op.alter_column('scan_result', 'high_severity_count',
                    new_column_name='highseverity_count')
    op.alter_column('scan_result', 'critical_severity_count',
                    new_column_name='criticalseverity_count')
    
    # Удаляем добавленные колонки
    op.drop_column('stage_run', 'stage_output_status')
    op.drop_column('process_run', 'error_message')
    op.drop_column('process_run', 'group_id')
    
    # Возвращаем JSON в job
    op.alter_column('job', 'hosts_data',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    type_=sa.Text(),
                    existing_nullable=True)
    op.alter_column('job', 'groups_data',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    type_=sa.Text(),
                    existing_nullable=True)
    # ### end Alembic commands ###
