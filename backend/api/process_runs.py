from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.process_run import ProcessRunCreate, ProcessRunResponse, ProcessRunList
from ..services import process_run_service

router = APIRouter(prefix="/api/process-runs", tags=["Сессии сканирования"])


# --- СОЗДАНИЕ ---

@router.post("/", response_model=ProcessRunResponse, status_code=status.HTTP_201_CREATED)
async def create_process_run(
    process_data: ProcessRunCreate,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую сессию сканирования."""
    return await process_run_service.create_process_run(db, process_data, user_login)


# --- СПИСОК ---

@router.get("/", response_model=List[ProcessRunList])
async def get_process_runs(
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех сессий сканирования."""
    return await process_run_service.get_all_process_runs(db, skip=skip, limit=limit)


# --- УПРАВЛЕНИЕ ---

@router.post("/{process_run_id}/start", response_model=ProcessRunResponse)
async def start_process_run(
    process_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """Запустить или возобновить сессию (из IDLE или HOLD)."""
    return await process_run_service.start_process_run(db, process_run_id, user_login)


@router.post("/{process_run_id}/hold", response_model=ProcessRunResponse)
async def hold_process_run(
    process_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """Приостановить сессию (перевести в HOLD)."""
    return await process_run_service.hold_process_run(db, process_run_id, user_login)


@router.post("/{process_run_id}/cancel", response_model=ProcessRunResponse)
async def cancel_process_run(
    process_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """Окончательно отменить сессию."""
    return await process_run_service.cancel_process_run(db, process_run_id, user_login)


@router.post("/{process_run_id}/reset", response_model=ProcessRunResponse)
async def reset_process_run(
    process_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """Сбросить сессию к начальному состоянию (IDLE)."""
    return await process_run_service.reset_process_run(db, process_run_id, user_login)


# --- ПОЛУЧЕНИЕ И УДАЛЕНИЕ ---

@router.get("/{process_run_id}", response_model=ProcessRunResponse)
async def get_process_run(
    process_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить сессию по ID."""
    return await process_run_service.get_process_run(db, process_run_id)


@router.delete("/{process_run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process_run(
    process_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """Удалить сессию сканирования."""
    await process_run_service.delete_process_run(db, process_run_id, user_login)