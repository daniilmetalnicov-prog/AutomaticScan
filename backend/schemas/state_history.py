from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StateHistoryResponse(BaseModel):
    """Схема для ответа (полная информация о переходе состояния)."""
    id: int
    process_run_id: int
    stage_run_id: Optional[int] = None
    entity_type: str  # "process_run" или "stage_run"
    from_status: Optional[str] = None
    to_status: str
    transition_type: str  # USER_ACTION, SYSTEM_AUTO, DMN_DECISION, ERROR
    reason: Optional[str] = None
    triggered_by: str
    transition_at: datetime
    
    class Config:
        from_attributes = True