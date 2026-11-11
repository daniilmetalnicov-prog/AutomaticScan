from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from .stage_run import StageRunResponse


class ProcessRunCreate(BaseModel):
    """Схема для создания сессии сканирования."""
    group_id: int
    stages: List[str]
    initiated_by: str = "manual"
    
    @field_validator("initiated_by")
    @classmethod
    def validate_initiated_by(cls, v: str) -> str:
        if v not in ["manual", "scheduled"]:
            raise ValueError("Режим запуска должен быть 'manual' или 'scheduled'")
        return v
    
    @field_validator("stages")
    @classmethod
    def validate_stages(cls, v: List[str]) -> List[str]:
        valid_stages = [
            "Актуализация объектов",
            "Проверка доступности",
            "Аудит уязвимостей",
            "Размещение отчетов",
            "Формирование аналитики"
        ]
        for stage in v:
            if stage not in valid_stages:
                raise ValueError(f"Недопустимый этап: {stage}. Допустимые: {valid_stages}")
        return v


class ProcessRunResponse(BaseModel):
    """Схема для ответа (полная информация о сессии)."""
    id: int
    group_id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str  # IDLE, IN_PROGRESS, SUCCESS, SKIPPED, HOLD, CANCELLED, FAILED
    initiated_by: str
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProcessRunList(BaseModel):
    """Схема для списка сессий с этапами."""
    id: int
    group_id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str
    initiated_by: str
    error_message: Optional[str] = None
    stages: List[StageRunResponse] = []
    
    class Config:
        from_attributes = True