from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from core.database import Base


class Host(Base):
    """Модель хоста из RedCheck."""
    __tablename__ = "host"
    
    # Внутренний ID для связей в БД
    id = Column(Integer, primary_key=True)
    
    # ID группы, к которой принадлежит хост
    group_id = Column(Integer, ForeignKey("group.id", ondelete="CASCADE"), nullable=False)
    
    # ID хоста в RedCheck (внешний ключ)
    redcheck_id = Column(Integer, nullable=True)
    
    # Уникальный идентификатор хоста из RedCheck
    guid = Column(String(36), nullable=True)
    
    # Универсальный уникальный идентификатор
    uuid = Column(String(36), nullable=True)
    
    # IP-адрес или имя хоста (из RedCheck connectionAddress)
    connection_address = Column(String(255), nullable=False)
    
    # Описание хоста (из RedCheck description)
    description = Column(Text, nullable=True)
    
    # CPE хоста (название и версия ОС)
    cpe = Column(String(255), nullable=True)
    
    # Является ли connectionAddress именем (true) или IP (false)
    is_dns = Column(Boolean, nullable=False, server_default="false")
    
    # Дата последнего изменения хоста
    modification_date = Column(DateTime, nullable=True)
    
    # ID сегмента, в который входит хост
    segment_id = Column(Integer, nullable=True)
    
    # Флаг: хост удалён в RedCheck
    is_deleted_in_redcheck = Column(Boolean, nullable=False, server_default="false")
    
    # Уникальное ограничение: один хост может быть только один раз в группе
    __table_args__ = (
        UniqueConstraint('group_id', 'redcheck_id', name='uq_host_group_redcheck'),
        Index('idx_host_group_id', 'group_id'),
        Index('idx_host_redcheck_id', 'redcheck_id'),
        Index('idx_host_connection_address', 'connection_address'),
        {'extend_existing': True}
    )
    
    # Связи
    group = relationship("Group", back_populates="hosts")
    scan_results = relationship("ScanResult", back_populates="host")

    # Если Таблица была создана через SQL-скрипты
    __table_args__ = {'extend_existing': True}