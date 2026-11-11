from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.process_log import ProcessLogCreate, ProcessLogResponse
from ..services import process_log_service

router = APIRouter(prefix="/api/process-logs", tags=["Логи процессов"])


# ============================================================
# ВАЖНО: порядок маршрутов критичен для FastAPI!
# Конкретные маршруты (без параметров в пути) должны идти
# ПЕРЕД маршрутами с параметрами (/{log_id})
# ============================================================


# --- СОЗДАНИЕ ---

@router.post("/", response_model=ProcessLogResponse, status_code=201)
async def create_process_log(
    log_data: ProcessLogCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать запись лога процесса."""
    return await process_log_service.create_process_log(db, log_data)


# --- ЧТЕНИЕ ПО СВЯЗЯМ (конкретные маршруты) ---

@router.get("/stage/{stage_run_id}", response_model=List[ProcessLogResponse])
async def get_logs_by_stage(
    stage_run_id: int,
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить логи для конкретного этапа сканирования."""
    return await process_log_service.get_logs_by_stage(
        db, stage_run_id, skip=skip, limit=limit
    )


@router.get("/process/{process_run_id}", response_model=List[ProcessLogResponse])
async def get_logs_by_process(
    process_run_id: int,
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить логи для конкретной сессии сканирования.
    
    Включает логи всех этапов сессии.
    """
    return await process_log_service.get_logs_by_process_run(
        db, process_run_id, skip=skip, limit=limit
    )


# --- СПИСОК (параметрические маршруты - в конце!) ---

@router.get("/", response_model=List[ProcessLogResponse])
async def get_all_logs(
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить все логи процессов."""
    return await process_log_service.get_all_process_logs(
        db, skip=skip, limit=limit
    )