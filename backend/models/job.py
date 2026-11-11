from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Table, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB  # ← JSONB импортируется из диалекта PostgreSQL
from sqlalchemy.orm import relationship
from core.database import Base


# Промежуточная таблица связи Job-Host (Many-to-Many)
# Имя таблицы 'job_host' передаётся первым позиционным аргументом
# PrimaryKeyConstraint с явным именем 'pk_job_host' нужен для корректной работы миграций Alembic
job_host = Table(
    'job_host',  # ← Имя таблицы (первый позиционный аргумент)
    Base.metadata,
    Column('job_id', Integer, ForeignKey('job.id', ondelete='CASCADE')),
    Column('host_id', Integer, ForeignKey('host.id', ondelete='CASCADE')),
    PrimaryKeyConstraint('job_id', 'host_id', name='pk_job_host')  # ← Явное имя PK
)


# Промежуточная таблица связи Job-Group (Many-to-Many)
# Аналогично job_host — явное имя таблицы и первичного ключа
job_group = Table(
    'job_group',  # ← Имя таблицы (первый позиционный аргумент)
    Base.metadata,
    Column('job_id', Integer, ForeignKey('job.id', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('group.id', ondelete='CASCADE')),
    PrimaryKeyConstraint('job_id', 'group_id', name='pk_job_group')  # ← Явное имя PK
)


class Job(Base):
    """Модель задания (Job) из RedCheck."""
    __tablename__ = "job"
    
    # Внутренний ID для связей в БД
    id = Column(Integer, primary_key=True)
    
    # ID задания в RedCheck (внешний ключ)
    redcheck_id = Column(Integer, unique=True, nullable=True)
    
    # Уникальный идентификатор задания из RedCheck
    guid = Column(String(36), nullable=True)
    
    # Название задания
    name = Column(String(255), nullable=False)
    
    # Описание задания
    description = Column(Text, nullable=True)
    
    # Тип задания (1-Аудит конфигураций, 5-Аудит уязвимостей и т.д.)
    scan_type = Column(Integer, nullable=True)
    
    # Статус задания (0-Выполняется, 3-Завершено и т.д.)
    state = Column(Integer, nullable=True)
    
    # Метод сканирования (0-бежагент, 1-агент, 2-бежагент WinRM)
    agent_type = Column(Integer, nullable=True)
    
    # Дата создания задания
    creation_date = Column(DateTime, nullable=True)
    
    # Дата последнего изменения задания
    modification_date = Column(DateTime, nullable=True)
    
    # Сырые данные о хостах из RedCheck (JSONB) — используется JSONB для лучшей производительности
    hosts_data = Column(JSONB, nullable=True)
    
    # Сырые данные о группах из RedCheck (JSONB) — используется JSONB для лучшей производительности
    groups_data = Column(JSONB, nullable=True)
    
    # Флаг: задание удалено в RedCheck
    is_deleted_in_redcheck = Column(Boolean, nullable=False, server_default="false")
    
    # Связи Many-to-Many
    hosts = relationship("Host", secondary=job_host, backref="jobs")
    groups = relationship("Group", secondary=job_group, backref="jobs")
    
    __table_args__ = {'extend_existing': True}