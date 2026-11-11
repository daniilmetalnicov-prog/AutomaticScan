"""add_dmn_rules_table

Revision ID: 67e14ea3f608
Revises: c0a37aa6478a
Create Date: 2026-11-08 20:50:02.916587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '67e14ea3f608'
down_revision: Union[str, Sequence[str], None] = 'c0a37aa6478a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаём таблицу dmn_rules для хранения матрицы решений."""
    
    op.create_table('dmn_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('current_stage', sa.String(length=100), nullable=False),
        sa.Column('is_stage_included', sa.Boolean(), nullable=False),
        sa.Column('stage_output_status', sa.String(length=50), nullable=True),
        sa.Column('target_next_stage', sa.String(length=100), nullable=False),
        sa.Column('gate_decision', sa.String(length=20), nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('email_alert', sa.String(length=50), nullable=True),
        sa.Column('annotations', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_dmn_rules')
    )
    
    # Создаём индекс для ускорения поиска правил
    op.create_index('idx_dmn_rules_lookup', 'dmn_rules', 
                    ['current_stage', 'is_stage_included', 'stage_output_status'])


def downgrade() -> None:
    """Откат изменений: удаляем таблицу dmn_rules."""
    op.drop_index('idx_dmn_rules_lookup', 'dmn_rules')
    op.drop_table('dmn_rules')
    # ### end Alembic commands ###
