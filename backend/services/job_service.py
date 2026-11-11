from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from ..models.job import Job, job_host, job_group
from ..schemas.job import JobResponse, JobSyncResult


async def get_job(db: AsyncSession, job_id: int) -> Job:
    """Получает задание по внутреннему ID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено"
        )
    
    return job


async def get_job_by_redcheck_id(db: AsyncSession, redcheck_id: int) -> Job:
    """Получает задание по ID из RedCheck."""
    result = await db.execute(select(Job).where(Job.redcheck_id == redcheck_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено"
        )
    
    return job


async def get_job_by_name(db: AsyncSession, name: str) -> List[Job]:
    """Ищет задания по имени (частичное совпадение)."""
    result = await db.execute(
        select(Job).where(Job.name.ilike(f"%{name}%"))
    )
    return result.scalars().all()


async def get_all_jobs(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Job]:
    """Получает список всех заданий (не удалённых в RedCheck)."""
    result = await db.execute(
        select(Job).where(Job.is_deleted_in_redcheck == False).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def delete_job(db: AsyncSession, job_id: int) -> None:
    """Удаляет задание из БД (не из RedCheck)."""
    job = await get_job(db, job_id)
    await db.delete(job)
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


async def sync_jobs_from_redcheck(db: AsyncSession, redcheck_jobs: List[Dict[str, Any]]) -> JobSyncResult:
    """
    Синхронизирует задания из RedCheck с БД.
    
    Логика:
    1. Получаем список заданий из RedCheck
    2. Сравниваем с БД:
       - Есть в RedCheck, нет в БД → создаём новые
       - Есть в БД, нет в RedCheck → помечаем как удалённые
       - Есть и там и там → обновляем данные
    3. Возвращаем результат синхронизации
    """
    new_jobs = []
    deleted_jobs = []
    updated_jobs = []
    
    # Получаем все задания из БД
    result = await db.execute(select(Job))
    db_jobs = {job.redcheck_id: job for job in result.scalars().all() if job.redcheck_id}
    
    # Создаём словарь заданий из RedCheck по redcheck_id
    redcheck_dict = {job['id']: job for job in redcheck_jobs}
    
    # Проверяем задания из RedCheck
    for redcheck_id, redcheck_data in redcheck_dict.items():
        if redcheck_id in db_jobs:
            # Задание есть в БД → обновляем данные
            job = db_jobs[redcheck_id]
            job.name = redcheck_data.get('name', job.name)
            job.description = redcheck_data.get('description', job.description)
            job.scan_type = redcheck_data.get('scanType', job.scan_type)
            job.state = redcheck_data.get('state', job.state)
            job.agent_type = redcheck_data.get('agentType', job.agent_type)
            job.guid = redcheck_data.get('guid', job.guid)
            
            # Сохраняем сырые данные о хостах и группах
            job.hosts_data = redcheck_data.get('hosts', [])
            job.groups_data = redcheck_data.get('groups', [])
            
            # Парсим даты
            job.creation_date = parse_redcheck_date(redcheck_data.get('creationDate'))
            job.modification_date = parse_redcheck_date(redcheck_data.get('modificationDate'))
            
            # Сбрасываем флаг удаления
            job.is_deleted_in_redcheck = False
            
            updated_jobs.append(job)
        else:
            # Задания нет в БД → создаём новое
            new_job = Job(
                redcheck_id=redcheck_id,
                guid=redcheck_data.get('guid'),
                name=redcheck_data.get('name', ''),
                description=redcheck_data.get('description'),
                scan_type=redcheck_data.get('scanType'),
                state=redcheck_data.get('state'),
                agent_type=redcheck_data.get('agentType'),
                hosts_data=redcheck_data.get('hosts', []),
                groups_data=redcheck_data.get('groups', []),
                is_deleted_in_redcheck=False
            )
            
            # Парсим даты
            new_job.creation_date = parse_redcheck_date(redcheck_data.get('creationDate'))
            new_job.modification_date = parse_redcheck_date(redcheck_data.get('modificationDate'))
            
            db.add(new_job)
            await db.flush()
            await db.refresh(new_job)
            new_jobs.append(new_job)
    
    # Проверяем задания в БД, которых нет в RedCheck
    for redcheck_id, job in db_jobs.items():
        if redcheck_id not in redcheck_dict:
            job.is_deleted_in_redcheck = True
            deleted_jobs.append(job)
    
    await db.flush()
    
    return JobSyncResult(
        new_jobs=new_jobs,
        deleted_jobs=deleted_jobs,
        updated_jobs=updated_jobs,
        total_synced=len(redcheck_jobs)
    )