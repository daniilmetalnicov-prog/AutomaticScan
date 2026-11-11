from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class StageRunResponse(BaseModel):
    """Схема для ответа (полная информация об этапе)."""
    id: int
    process_run_id: int
    current_stage: str
    redcheck_job_id: Optional[str] = None
    is_stage_included: bool
    status: str
    gate_decision: Optional[str] = None
    stage_output_status: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    hold_data: Optional[Dict[str, Any]] = None  # ← Добавлено
    
    class Config:
        from_attributes = True