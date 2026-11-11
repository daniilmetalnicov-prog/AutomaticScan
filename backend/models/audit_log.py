from sqlalchemy import Column, Integer, String, Text, DateTime
from core.database import Base
from datetime import datetime


class AuditLog(Base):
    """Модель аудита действий пользователей."""
    __tablename__ = "audit_log"
    
    # Внутренний ID записи аудита
    id = Column(Integer, primary_key=True)
    
    # Логин пользователя, выполнившего действие
    user_login = Column(String(50), nullable=False)
    
    # Тип действия (CREATE_SESSION, DELETE_SESSION, и т.д.)
    action_type = Column(String(50), nullable=False)
    
    # Сообщение с описанием действия
    message = Column(Text, nullable=False)
    
    # Время создания записи аудита
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = {'extend_existing': True}