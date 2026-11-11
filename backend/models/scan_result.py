from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class ScanResult(Base):
    """Модель результатов сканирования."""
    __tablename__ = "scan_result"
    
    # Внутренний ID результата сканирования
    id = Column(Integer, primary_key=True)
    
    # ID сессии сканирования
    process_run_id = Column(Integer, ForeignKey("process_run.id", ondelete="CASCADE"), nullable=False)
    
    # ID хоста
    host_id = Column(Integer, ForeignKey("host.id", ondelete="CASCADE"), nullable=False)
    
    # Доступен ли хост
    is_accessible = Column(Boolean, nullable=False, server_default="false")
    
    # Количество уязвимостей низкой критичности
    low_severity_count = Column(Integer, nullable=False, server_default="0")
    
    # Количество уязвимостей средней критичности
    medium_severity_count = Column(Integer, nullable=False, server_default="0")
    
    # Количество уязвимостей высокой критичности
    high_severity_count = Column(Integer, nullable=False, server_default="0")
    
    # Количество уязвимостей критической критичности
    critical_severity_count = Column(Integer, nullable=False, server_default="0")
    
    # Связи
    process_run = relationship("ProcessRun", back_populates="scan_results")
    host = relationship("Host", back_populates="scan_results")
    
    __table_args__ = {'extend_existing': True}