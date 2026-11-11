"""add_system_config_table

Revision ID: 84ff528b98c2
Revises: 67e14ea3f608
Create Date: 2026-11-08 22:34:34.148387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '84ff528b98c2'
down_revision: Union[str, Sequence[str], None] = '67e14ea3f608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаём таблицу system_config для хранения настроек системы."""
    
    op.create_table('system_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False, unique=True),
        sa.Column('config_value', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name='pk_system_config'),
        sa.UniqueConstraint('config_key', name='uq_system_config_key')
    )
    
    # Вставляем настройки по умолчанию
    op.execute("""
        INSERT INTO system_config (config_key, config_value, description) VALUES
        ('stuck_session_timeout_hours', '24', 'Максимальное время выполнения сессии в часах. После этого сессия считается зависшей.'),
        ('redcheck_polling_timeout_seconds', '300', 'Таймаут ожидания ответа от RedCheck API в секундах.'),
        ('max_retry_attempts', '3', 'Максимальное количество попыток при ошибках polling.'),
        ('health_check_interval_minutes', '5', 'Интервал проверки здоровья системы в минутах.'),
        ('auto_reset_stuck_sessions', 'true', 'Автоматически сбрасывать зависшие сессии (true/false).')
    """)


def downgrade() -> None:
    """Откат изменений: удаляем таблицу system_config."""
    op.drop_table('system_config')
    # ### end Alembic commands ###
