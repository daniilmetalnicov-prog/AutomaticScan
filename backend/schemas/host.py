from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class HostResponse(BaseModel):
    """Схема для ответа (полная информация о хосте)."""
    id: int  						# Внутренний ID в БД
    group_id: int  					# ID группы
    redcheck_id: Optional[int] = None  			# ID хоста в RedCheck
    guid: Optional[str] = None  			# Уникальный идентификатор из RedCheck
    uuid: Optional[str] = None  			# Универсальный уникальный идентификатор
    connection_address: str  				# IP-адрес или имя хоста
    description: Optional[str] = None 	 		# Описание хоста
    cpe: Optional[str] = None  				# CPE хоста
    is_dns: bool  					# Является ли connectionAddress именем
    modification_date: Optional[datetime] = None  	# Дата последнего изменения
    segment_id: Optional[int] = None  			# ID сегмента
    is_deleted_in_redcheck: bool  			# Флаг удаления в RedCheck
    
    class Config:
        from_attributes = True


class HostSyncResult(BaseModel):
    """Схема для результата синхронизации хостов."""
    new_hosts: List[HostResponse] = []  		# Новые хосты
    deleted_hosts: List[HostResponse] = []  		# Удалённые хосты
    updated_hosts: List[HostResponse] = []  		# Обновлённые хосты
    total_synced: int  					# Общее количество синхронизированных хостов