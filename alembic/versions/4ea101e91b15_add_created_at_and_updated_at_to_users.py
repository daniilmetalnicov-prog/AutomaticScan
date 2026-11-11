"""add created_at and updated_at to users

Revision ID: 4ea101e91b15
Revises: 6ff977123c20
Create Date: 2026-11-06 18:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4ea101e91b15'
down_revision: Union[str, None] = '6ff977123c20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')