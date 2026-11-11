from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScanResultCreate(BaseModel):
    """Схема для создания результата сканирования."""
    process_run_id: int  		# ID сессии
    host_id: int  			# ID хоста
    is_accessible: bool = False  	# Доступен ли хост
    low_severity_count: int = 0  	# Уязвимости низкой критичности
    medium_severity_count: int = 0  	# Уязвимости средней критичности
    high_severity_count: int = 0  	# Уязвимости высокой критичности
    critical_severity_count: int = 0  	# Уязвимости критической критичности


class ScanResultResponse(BaseModel):
    """Схема для ответа (полная информация о результате)."""
    id: int
    process_run_id: int
    host_id: int
    is_accessible: bool
    low_severity_count: int
    medium_severity_count: int
    high_severity_count: int
    critical_severity_count: int
    
    class Config:
        from_attributes = True