from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class ProcessLogCreate(BaseModel):
    """Схема для создания записи лога процесса."""
    process_run_id: Optional[int] = None  # ← Добавлено
    stage_run_id: Optional[int] = None
    log_level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str  # Текст сообщения
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Проверяет, что уровень логирования допустим."""
        valid_levels = ["INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"Недопустимый уровень: {v}. Допустимые: {valid_levels}")
        return v


class ProcessLogResponse(BaseModel):
    """Схема для ответа (полная информация о записи лога)."""
    id: int
    process_run_id: Optional[int] = None  # ← Добавлено
    stage_run_id: Optional[int] = None
    log_level: str
    message: str
    created_at: datetime
    
    class Config:
        from_attributes = True