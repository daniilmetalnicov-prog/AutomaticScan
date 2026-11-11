from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime


class StateHistory(Base):
    """Модель истории переходов состояний FSM."""
    __tablename__ = "state_history"
    
    # Внутренний ID записи истории
    id = Column(Integer, primary_key=True)
    
    # ID сессии, к которой относится переход
    process_run_id = Column(Integer, ForeignKey("process_run.id", ondelete="CASCADE"), nullable=False)
    
    # ID этапа (nullable, т.к. переход может быть на уровне сессии)
    stage_run_id = Column(Integer, ForeignKey("stage_run.id", ondelete="CASCADE"), nullable=True)
    
    # Тип сущности: "process_run" или "stage_run"
    entity_type = Column(String(20), nullable=False)
    
    # Предыдущий статус (может быть NULL при создании)
    from_status = Column(String(30), nullable=True)
    
    # Новый статус
    to_status = Column(String(30), nullable=False)
    
    # Тип перехода: USER_ACTION, SYSTEM_AUTO, DMN_DECISION, ERROR
    transition_type = Column(String(20), nullable=False)
    
    # Причина перехода (описание)
    reason = Column(Text, nullable=True)
    
    # Кто инициировал переход (логин пользователя или "system")
    triggered_by = Column(String(50), nullable=False)
    
    # Время перехода
    transition_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Связи
    process_run = relationship("ProcessRun", backref="state_history")
    stage_run = relationship("StageRun", backref="state_history")
    
    __table_args__ = {'extend_existing': True}