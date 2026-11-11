from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class JobResponse(BaseModel):
    """Схема для ответа (полная информация о задании)."""
    id: int  							# Внутренний ID в БД
    redcheck_id: Optional[int] = None  				# ID задания в RedCheck
    guid: Optional[str] = None  				# Уникальный идентификатор из RedCheck
    name: str  							# Название задания
    description: Optional[str] = None  				# Описание задания
    scan_type: Optional[int] = None  				# Тип задания
    state: Optional[int] = None  				# Статус задания
    agent_type: Optional[int] = None  				# Метод сканирования
    creation_date: Optional[datetime] = None  			# Дата создания
    modification_date: Optional[datetime] = None  		# Дата изменения
    hosts_data: Optional[List[Dict[str, Any]]] = None  		# Сырые данные о хостах (список словарей)
    groups_data: Optional[List[Dict[str, Any]]] = None  	# Сырые данные о группах (список словарей)
    is_deleted_in_redcheck: bool  				# Флаг удаления в RedCheck
    
    class Config:
        from_attributes = True


class JobSyncResult(BaseModel):
    """Схема для результата синхронизации заданий."""
    new_jobs: List[JobResponse] = []  				# Новые задания
    deleted_jobs: List[JobResponse] = []  			# Удалённые задания
    updated_jobs: List[JobResponse] = []  			# Обновлённые задания
    total_synced: int  						# Общее количество синхронизированных заданий