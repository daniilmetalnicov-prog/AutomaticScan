from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from core.database import Base


class StageRun(Base):
    """Модель этапа сканирования."""
    __tablename__ = "stage_run"
    
    id = Column(Integer, primary_key=True)
    process_run_id = Column(Integer, ForeignKey("process_run.id", ondelete="CASCADE"), nullable=False)
    current_stage = Column(String(100), nullable=False)
    redcheck_job_id = Column(String(100), nullable=True)
    is_stage_included = Column(Boolean, nullable=False, default=True)
    status = Column(String(30), nullable=False, default="IDLE")
    gate_decision = Column(String(20), nullable=True)
    stage_output_status = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # Контекст HOLD: {"phase": "REDCHECK"|"DB", "hosts_to_delete": [...]}
    hold_data = Column(JSON, nullable=True)
    
    process_run = relationship("ProcessRun", back_populates="stages")
    process_logs = relationship("ProcessLog", back_populates="stage_run")
    
    __table_args__ = {'extend_existing': True}