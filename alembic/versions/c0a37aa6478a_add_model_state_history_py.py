"""add model state_history.py

Revision ID: c0a37aa6478a
Revises: 33cb890665c4
Create Date: 2026-11-08 19:28:47.215570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c0a37aa6478a'
down_revision: Union[str, Sequence[str], None] = '33cb890665c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаём таблицу state_history для логирования переходов FSM."""
    
    op.create_table('state_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('process_run_id', sa.Integer(), nullable=False),
        sa.Column('stage_run_id', sa.Integer(), nullable=True),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('from_status', sa.String(length=30), nullable=True),
        sa.Column('to_status', sa.String(length=30), nullable=False),
        sa.Column('transition_type', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('triggered_by', sa.String(length=50), nullable=False),
        sa.Column('transition_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_state_history'),
        sa.ForeignKeyConstraint(['process_run_id'], ['process_run.id'], 
                                name='fk_state_history_process_run', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_run_id'], ['stage_run.id'], 
                                name='fk_state_history_stage_run', ondelete='CASCADE')
    )
    
    # Создаём индексы для ускорения запросов
    op.create_index('idx_state_history_process_run', 'state_history', ['process_run_id'])
    op.create_index('idx_state_history_stage_run', 'state_history', ['stage_run_id'])
    op.create_index('idx_state_history_transition_at', 'state_history', ['transition_at'])


def downgrade() -> None:
    """Откат изменений: удаляем таблицу state_history."""
    op.drop_index('idx_state_history_transition_at', 'state_history')
    op.drop_index('idx_state_history_stage_run', 'state_history')
    op.drop_index('idx_state_history_process_run', 'state_history')
    op.drop_table('state_history')
    # ### end Alembic commands ###
