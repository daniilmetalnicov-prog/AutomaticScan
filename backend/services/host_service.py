from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from ..models.host import Host
from ..schemas.host import HostResponse, HostSyncResult


async def get_host(db: AsyncSession, host_id: int) -> Host:
    """Получает хост по внутреннему ID."""
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Хост не найден"
        )
    
    return host


async def get_host_by_redcheck_id(db: AsyncSession, redcheck_id: int) -> Host:
    """Получает хост по ID из RedCheck."""
    result = await db.execute(select(Host).where(Host.redcheck_id == redcheck_id))
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Хост не найден"
        )
    
    return host


async def get_hosts_by_group(db: AsyncSession, group_id: int, skip: int = 0, limit: int = 100) -> List[Host]:
    """Получает список хостов для конкретной группы."""
    result = await db.execute(
        select(Host)
        .where(Host.group_id == group_id, Host.is_deleted_in_redcheck == False)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_host_by_connection_address(db: AsyncSession, connection_address: str) -> List[Host]:
    """Ищет хосты по IP-адресу или имени (частичное совпадение)."""
    result = await db.execute(
        select(Host).where(Host.connection_address.ilike(f"%{connection_address}%"))
    )
    return result.scalars().all()


async def delete_host(db: AsyncSession, host_id: int) -> None:
    """Удаляет хост из БД (не из RedCheck)."""
    host = await get_host(db, host_id)
    await db.delete(host)
    await db.flush()


def parse_redcheck_date(date_string: str) -> datetime:
    """
    Парсит дату из RedCheck и убирает timezone.
    
    RedCheck возвращает даты в формате "2023-02-06T13:09:25.181Z"
    Колонка в БД имеет тип timestamp without time zone,
    поэтому нужно убрать timezone информацию.
    """
    if not date_string:
        return None
    
    try:
        # Заменяем Z на +00:00 для корректного парсинга
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        # Убираем timezone, так как колонка в БД без timezone
        return dt.replace(tzinfo=None)
    except ValueError:
        return None


async def sync_hosts_from_redcheck(
    db: AsyncSession, 
    group_id: int, 
    redcheck_hosts: List[Dict[str, Any]]
) -> HostSyncResult:
    """
    Синхронизирует хосты из RedCheck с БД для конкретной группы.
    
    Логика:
    1. Получаем список хостов из RedCheck для группы
    2. Сравниваем с БД:
       - Есть в RedCheck, нет в БД → создаём новые
       - Есть в БД, нет в RedCheck → помечаем как удалённые
       - Есть и там и там → обновляем данные
    3. Возвращаем результат синхронизации
    """
    new_hosts = []
    deleted_hosts = []
    updated_hosts = []
    
    # Получаем все хосты для этой группы из БД
    result = await db.execute(
        select(Host).where(Host.group_id == group_id)
    )
    db_hosts = {host.redcheck_id: host for host in result.scalars().all() if host.redcheck_id}
    
    # Создаём словарь хостов из RedCheck по redcheck_id
    redcheck_dict = {host['id']: host for host in redcheck_hosts}
    
    # Проверяем хосты из RedCheck
    for redcheck_id, redcheck_data in redcheck_dict.items():
        if redcheck_id in db_hosts:
            # Хост есть в БД → обновляем данные
            host = db_hosts[redcheck_id]
            host.connection_address = redcheck_data.get('connectionAddress', host.connection_address)
            host.description = redcheck_data.get('description', host.description)
            host.cpe = redcheck_data.get('cpe', host.cpe)
            host.is_dns = redcheck_data.get('isDns', False)
            host.segment_id = redcheck_data.get('segmentId', host.segment_id)
            host.guid = redcheck_data.get('guid', host.guid)
            host.uuid = redcheck_data.get('uuid', host.uuid)
            
            # Парсим дату изменения
            host.modification_date = parse_redcheck_date(redcheck_data.get('modificationDate'))
            
            # Сбрасываем флаг удаления
            host.is_deleted_in_redcheck = False
            
            updated_hosts.append(host)
        else:
            # Хоста нет в БД → создаём новый
            new_host = Host(
                group_id=group_id,
                redcheck_id=redcheck_id,
                guid=redcheck_data.get('guid'),
                uuid=redcheck_data.get('uuid'),
                connection_address=redcheck_data.get('connectionAddress', ''),
                description=redcheck_data.get('description'),
                cpe=redcheck_data.get('cpe'),
                is_dns=redcheck_data.get('isDns', False),
                segment_id=redcheck_data.get('segmentId'),
                is_deleted_in_redcheck=False
            )
            
            # Парсим дату изменения
            new_host.modification_date = parse_redcheck_date(redcheck_data.get('modificationDate'))
            
            db.add(new_host)
            await db.flush()
            await db.refresh(new_host)
            new_hosts.append(new_host)
    
    # Проверяем хосты в БД, которых нет в RedCheck
    for redcheck_id, host in db_hosts.items():
        if redcheck_id not in redcheck_dict:
            host.is_deleted_in_redcheck = True
            deleted_hosts.append(host)
    
    await db.flush()
    
    return HostSyncResult(
        new_hosts=new_hosts,
        deleted_hosts=deleted_hosts,
        updated_hosts=updated_hosts,
        total_synced=len(redcheck_hosts)
    )