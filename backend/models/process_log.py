from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from core.database import Base


class ProcessLog(Base):
    """Модель системного лога процесса."""
    __tablename__ = "process_log"
    
    # Внутренний ID записи лога
    id = Column(Integer, primary_key=True)
    
    # ID сессии (nullable — для общих системных действий)
    process_run_id = Column(Integer, ForeignKey("process_run.id", ondelete="CASCADE"), nullable=True)
    
    # ID этапа (nullable — для системных действий, не привязанных к этапу)
    stage_run_id = Column(Integer, ForeignKey("stage_run.id", ondelete="CASCADE"), nullable=True)
    
    # Уровень логирования: INFO, WARNING, ERROR, CRITICAL
    log_level = Column(String(20), nullable=False)
    
    # Текст сообщения
    message = Column(Text, nullable=False)
    
    # Время создания записи
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Связи
    process_run = relationship("ProcessRun", backref="process_logs")
    stage_run = relationship("StageRun", back_populates="process_logs")
    
    __table_args__ = {'extend_existing': True}