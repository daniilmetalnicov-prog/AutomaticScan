from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.job import JobResponse, JobSyncResult
from ..services import job_service

# Создаём роутер с префиксом /api/jobs
router = APIRouter(prefix="/api/jobs", tags=["Задания"])


# ============================================================
# ВАЖНО: порядок маршрутов критичен для FastAPI!
# Конкретные маршруты (без параметров в пути) должны идти
# ПЕРЕД маршрутами с параметрами (/{job_id}), иначе FastAPI
# будет воспринимать "search", "redcheck" и т.д. как значения job_id
# ============================================================


# --- СИНХРОНИЗАЦИЯ ---

@router.post("/sync", response_model=JobSyncResult)
async def sync_jobs(
    redcheck_jobs: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизировать задания из RedCheck с БД.
    
    В реальном приложении здесь будет запрос к RedCheck API.
    Пока что принимаем список заданий в теле запроса для тестирования.
    """
    return await job_service.sync_jobs_from_redcheck(db, redcheck_jobs)


# --- ПОИСК ---

@router.get("/search", response_model=List[JobResponse])
async def search_jobs(
    name: str = Query(..., description="Название задания для поиска (частичное совпадение)"),
    db: AsyncSession = Depends(get_db)
):
    """Поиск заданий по имени."""
    return await job_service.get_job_by_name(db, name)


# --- СПИСОК ---

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех заданий (не удалённых в RedCheck)."""
    return await job_service.get_all_jobs(db, skip=skip, limit=limit)


# --- ПО ВНЕШНЕМУ ID ---

@router.get("/redcheck/{redcheck_id}", response_model=JobResponse)
async def get_job_by_redcheck_id(
    redcheck_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить задание по ID из RedCheck."""
    return await job_service.get_job_by_redcheck_id(db, redcheck_id)


# --- ПО ВНУТРЕННЕМУ ID ---

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить задание по внутреннему ID."""
    return await job_service.get_job(db, job_id)


# --- УДАЛЕНИЕ (всегда в конце!) ---

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить задание из БД (не из RedCheck).
    
    Внимание: это удаление только из локальной БД.
    Задание останется в сканере уязвимостей RedCheck.
    """
    await job_service.delete_job(db, job_id)