from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditLogCreate(BaseModel):
    """Схема для создания записи аудита."""
    user_login: str  # Логин пользователя (или 'system')
    action_type: str  # Тип действия
    message: str  # Описание действия


class AuditLogResponse(BaseModel):
    """Схема для ответа (полная информация о записи аудита)."""
    id: int
    user_login: str
    action_type: str
    message: str
    created_at: datetime
    
    class Config:
        from_attributes = True