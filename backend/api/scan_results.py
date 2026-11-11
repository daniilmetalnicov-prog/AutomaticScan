from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.scan_result import ScanResultCreate, ScanResultResponse
from ..services import scan_result_service

# Создаём роутер с префиксом /api/scan-results
router = APIRouter(prefix="/api/scan-results", tags=["Результаты сканирования"])


# ============================================================
# ВАЖНО: порядок маршрутов критичен для FastAPI!
# Конкретные маршруты (без параметров в пути) должны идти
# ПЕРЕД маршрутами с параметрами (/{result_id}), иначе FastAPI
# будет воспринимать "process", "host" как значения result_id
# ============================================================


# --- СОЗДАНИЕ ---

@router.post("/", response_model=ScanResultResponse, status_code=201)
async def create_scan_result(
    result_data: ScanResultCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать результат сканирования."""
    return await scan_result_service.create_scan_result(db, result_data)


# --- ЧТЕНИЕ ПО СВЯЗЯМ (конкретные маршруты) ---

@router.get("/process/{process_run_id}", response_model=List[ScanResultResponse])
async def get_results_by_process(
    process_run_id: int,
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить результаты для конкретной сессии сканирования."""
    return await scan_result_service.get_results_by_process_run(
        db, process_run_id, skip=skip, limit=limit
    )


@router.get("/host/{host_id}", response_model=List[ScanResultResponse])
async def get_results_by_host(
    host_id: int,
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить результаты для конкретного хоста."""
    return await scan_result_service.get_results_by_host(
        db, host_id, skip=skip, limit=limit
    )


# --- ПОЛУЧЕНИЕ ПО ID И УДАЛЕНИЕ (параметрические маршруты - в конце!) ---

@router.get("/{result_id}", response_model=ScanResultResponse)
async def get_scan_result(
    result_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить результат сканирования по ID."""
    return await scan_result_service.get_scan_result(db, result_id)


@router.delete("/{result_id}", status_code=204)
async def delete_scan_result(
    result_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удалить результат сканирования."""
    await scan_result_service.delete_scan_result(db, result_id)