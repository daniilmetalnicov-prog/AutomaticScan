from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class GroupResponse(BaseModel):
    """Схема для ответа (полная информация о группе)."""
    id: int  						# Внутренний ID в БД
    redcheck_id: Optional[int] = None  			# ID группы в RedCheck
    unique_id: Optional[str] = None  			# UUID группы из RedCheck
    name: str  						# Название группы
    description: Optional[str] = None  			# Описание группы
    modification_date: Optional[datetime] = None  	# Дата последнего изменения
    count_of_hosts: Optional[int] = None  		# Количество хостов
    segment_id: Optional[int] = None  			# ID сегмента
    is_active: bool  					# Флаг сканирования
    is_deleted_in_redcheck: bool  			# Флаг удаления в RedCheck
    
    class Config:
        from_attributes = True  			# Позволяет создавать схему из ORM-объекта


class GroupSyncResult(BaseModel):
    """Схема для результата синхронизации."""
    new_groups: List[GroupResponse] = []  		# Новые группы (есть в RedCheck, нет в БД)
    deleted_groups: List[GroupResponse] = []  		# Удалённые группы (есть в БД, нет в RedCheck)
    updated_groups: List[GroupResponse] = []  		# Обновлённые группы
    total_synced: int  					# Общее количество синхронизированных групп