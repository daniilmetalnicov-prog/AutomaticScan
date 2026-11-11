from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from ..models.group import Group
from ..schemas.group import GroupResponse, GroupSyncResult


async def get_group(db: AsyncSession, group_id: int) -> Group:
    """Получает группу по внутреннему ID."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена"
        )
    
    return group


async def get_group_by_redcheck_id(db: AsyncSession, redcheck_id: int) -> Group:
    """Получает группу по ID из RedCheck."""
    result = await db.execute(select(Group).where(Group.redcheck_id == redcheck_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена"
        )
    
    return group


async def get_group_by_name(db: AsyncSession, name: str) -> List[Group]:
    """Ищет группы по имени (частичное совпадение)."""
    result = await db.execute(
        select(Group).where(Group.name.ilike(f"%{name}%"))
    )
    return result.scalars().all()


async def get_all_groups(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Group]:
    """Получает список всех групп с пагинацией."""
    result = await db.execute(
        select(Group).where(Group.is_deleted_in_redcheck == False).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def delete_group(db: AsyncSession, group_id: int) -> None:
    """Удаляет группу из БД (не из RedCheck)."""
    group = await get_group(db, group_id)
    await db.delete(group)
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


async def sync_groups_from_redcheck(db: AsyncSession, redcheck_groups: List[Dict[str, Any]]) -> GroupSyncResult:
    """
    Синхронизирует группы из RedCheck с БД.
    
    Логика:
    1. Получаем список групп из RedCheck
    2. Сравниваем с БД:
       - Есть в RedCheck, нет в БД → создаём новые
       - Есть в БД, нет в RedCheck → помечаем как удалённые
       - Есть и там и там → обновляем данные
    3. Возвращаем результат синхронизации
    """
    new_groups = []
    deleted_groups = []
    updated_groups = []
    
    # Получаем все группы из БД
    result = await db.execute(select(Group))
    db_groups = {group.redcheck_id: group for group in result.scalars().all() if group.redcheck_id}
    
    # Создаём словарь групп из RedCheck по redcheck_id
    redcheck_dict = {group['id']: group for group in redcheck_groups}
    
    # Проверяем группы из RedCheck
    for redcheck_id, redcheck_data in redcheck_dict.items():
        if redcheck_id in db_groups:
            # Группа есть в БД → обновляем данные
            group = db_groups[redcheck_id]
            group.name = redcheck_data.get('name', group.name)
            group.description = redcheck_data.get('description', group.description)
            group.count_of_hosts = redcheck_data.get('countOfHosts', group.count_of_hosts)
            group.segment_id = redcheck_data.get('segmentId', group.segment_id)
            
            # Парсим дату изменения (убираем timezone)
            group.modification_date = parse_redcheck_date(redcheck_data.get('modificationDate'))
            
            # Сбрасываем флаг удаления
            group.is_deleted_in_redcheck = False
            
            updated_groups.append(group)
        else:
            # Группы нет в БД → создаём новую
            new_group = Group(
                redcheck_id=redcheck_id,
                unique_id=redcheck_data.get('uniqueId'),
                name=redcheck_data.get('name', ''),
                description=redcheck_data.get('description'),
                count_of_hosts=redcheck_data.get('countOfHosts', 0),
                segment_id=redcheck_data.get('segmentId'),
                is_active=False,
                is_deleted_in_redcheck=False
            )
            
            # Парсим дату изменения (убираем timezone)
            new_group.modification_date = parse_redcheck_date(redcheck_data.get('modificationDate'))
            
            db.add(new_group)
            await db.flush()
            await db.refresh(new_group)
            new_groups.append(new_group)
    
    # Проверяем группы в БД, которых нет в RedCheck
    for redcheck_id, group in db_groups.items():
        if redcheck_id not in redcheck_dict:
            group.is_deleted_in_redcheck = True
            deleted_groups.append(group)
    
    await db.flush()
    
    return GroupSyncResult(
        new_groups=new_groups,
        deleted_groups=deleted_groups,
        updated_groups=updated_groups,
        total_synced=len(redcheck_groups)
    )