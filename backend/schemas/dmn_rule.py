from pydantic import BaseModel
from typing import Optional


class DmnRuleResponse(BaseModel):
    """Схема для ответа (полная информация о правиле DMN)."""
    id: int
    current_stage: str
    is_stage_included: bool
    stage_output_status: Optional[str] = None
    target_next_stage: str
    gate_decision: str
    log_level: str
    email_alert: Optional[str] = None
    annotations: Optional[str] = None
    
    class Config:
        from_attributes = True


class DmnDecisionResponse(BaseModel):
    """Схема для ответа решения DMN."""
    rule_id: int
    current_stage: str
    stage_output_status: Optional[str] = None
    target_next_stage: str
    gate_decision: str
    log_level: str
    email_alert: Optional[str] = None
    annotations: Optional[str] = None