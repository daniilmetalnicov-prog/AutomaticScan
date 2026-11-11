from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from core.database import Base


class Group(Base):
    """Модель группы хостов из RedCheck."""
    __tablename__ = "group"
    
    # Внутренний ID для связей в БД
    id = Column(Integer, primary_key=True)
    
    # ID группы в RedCheck (внешний ключ)
    redcheck_id = Column(Integer, unique=True, nullable=True)
    
    # UUID группы из RedCheck
    unique_id = Column(String(36), unique=True, nullable=True)
    
    # Название группы
    name = Column(String(255), nullable=False)
    
    # Описание группы
    description = Column(Text, nullable=True)
    
    # Дата последнего изменения состава группы
    modification_date = Column(DateTime, nullable=True)
    
    # Количество хостов в группе
    count_of_hosts = Column(Integer, nullable=True, server_default="0")
    
    # ID сегмента, в который входит группа
    segment_id = Column(Integer, nullable=True)
    
    # Расписание сканирования (оставили из ERD)
    scan_schedule = Column(String(50), nullable=True)
    
    # Флаг: группа сейчас сканируется или нет
    is_active = Column(Boolean, nullable=False, server_default="false")
    
    # Флаг: группа удалена в RedCheck
    is_deleted_in_redcheck = Column(Boolean, nullable=False, server_default="false")
    
    # Связь с хостами
    hosts = relationship("Host", back_populates="group")
    
    # Если Таблица была создана через SQL-скрипты
    __table_args__ = {'extend_existing': True}