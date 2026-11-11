from sqlalchemy import Column, Integer, String, Boolean, Text
from core.database import Base


class DmnRule(Base):
    """Модель правила матрицы решений DMN."""
    __tablename__ = "dmn_rules"
    
    # Внутренний ID правила
    id = Column(Integer, primary_key=True)
    
    # Название текущего этапа
    current_stage = Column(String(100), nullable=False)
    
    # Включён ли этап (в текущей реализации всегда true для созданных этапов)
    is_stage_included = Column(Boolean, nullable=False)
    
    # Результат выполнения этапа (SUCCESS, FAILED, PARTIAL_SUCCESS и т.д.)
    stage_output_status = Column(String(50), nullable=True)
    
    # Целевой следующий этап
    target_next_stage = Column(String(100), nullable=False)
    
    # Решение шлюза: ALLOW, SKIP, HOLD, ABORT
    gate_decision = Column(String(20), nullable=False)
    
    # Уровень логирования: Log_Information, Log_Warning, Log_Critical
    log_level = Column(String(20), nullable=False)
    
    # Тип email-уведомления (nullable)
    email_alert = Column(String(50), nullable=True)
    
    # Аннотация (описание правила)
    annotations = Column(Text, nullable=True)
    
    __table_args__ = {'extend_existing': True}