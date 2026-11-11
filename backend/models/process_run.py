from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class ProcessRun(Base):
    """Модель сессии сканирования."""
    __tablename__ = "process_run"
    
    # Внутренний ID сессии
    id = Column(Integer, primary_key=True)
    
    # ID группы, для которой запускается сессия
    group_id = Column(Integer, ForeignKey("group.id", ondelete="SET NULL"), nullable=True)
    
    # Время запуска сессии
    started_at = Column(DateTime, nullable=True)
    
    # Время завершения сессии
    ended_at = Column(DateTime, nullable=True)
    
    # Статус сессии: IDLE, IN_PROGRESS, SUCCESS, FAILED, CANCELLED
    status = Column(String(30), nullable=False, server_default="IDLE")
    
    # Режим запуска: manual (вручную) или scheduled (по расписанию)
    initiated_by = Column(String(50), nullable=False, server_default="manual")
    
    # Краткое сообщение об ошибке (для отображения в реестре)
    error_message = Column(Text, nullable=True)
    
    # Связи
    stages = relationship("StageRun", back_populates="process_run", cascade="all, delete-orphan")
    scan_results = relationship("ScanResult", back_populates="process_run")
    
    __table_args__ = {'extend_existing': True}