from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from core.database import Base


class Report(Base):
    """Модель технического отчёта (этап 4: Размещение отчётов)."""
    __tablename__ = "report"
    
    id = Column(Integer, primary_key=True)
    stage_run_id = Column(Integer, ForeignKey("stage_run.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)  # Путь к файлу на сервере
    file_hash = Column(String(64), nullable=False)  # SHA-256 хэш файла
    network_path = Column(String(500), nullable=True)  # Путь в сетевой папке
    placed_at = Column(DateTime, nullable=True)  # Время размещения
    placement_status = Column(String(20), nullable=False, server_default="PENDING")  # PENDING/SUCCESS/FAILED
    
    stage_run = relationship("StageRun", backref="reports")
    
    __table_args__ = {'extend_existing': True}


class ReportTemplate(Base):
    """Модель шаблона отчёта (для этапа 5)."""
    __tablename__ = "report_template"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    format = Column(String(10), nullable=False)  # PDF/CSV
    template_data = Column(String, nullable=True)  # JSON с настройками
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = {'extend_existing': True}


class AnalyticsReport(Base):
    """Модель аналитического отчёта (этап 5: Формирование аналитики)."""
    __tablename__ = "analytics_report"
    
    id = Column(Integer, primary_key=True)
    process_run_id = Column(Integer, ForeignKey("process_run.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(Integer, ForeignKey("report_template.id", ondelete="SET NULL"), nullable=True)
    report_type = Column(String(10), nullable=False)  # PDF/CSV
    file_path = Column(String(500), nullable=False)
    generated_at = Column(DateTime, nullable=True)
    generation_status = Column(String(20), nullable=False, server_default="PENDING")  # PENDING/SUCCESS/FAILED
    
    process_run = relationship("ProcessRun", backref="analytics_reports")
    template = relationship("ReportTemplate")
    
    __table_args__ = {'extend_existing': True}