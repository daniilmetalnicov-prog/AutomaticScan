from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.state_history import StateHistoryResponse
from ..services import state_history_service

router = APIRouter(prefix="/api/state-history", tags=["История переходов FSM"])


@router.get("/process/{process_run_id}", response_model=List[StateHistoryResponse])
async def get_history_by_process(
    process_run_id: int,
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить историю переходов для конкретной сессии."""
    return await state_history_service.get_history_by_process_run(
        db, process_run_id, skip=skip, limit=limit
    )


@router.get("/stage/{stage_run_id}", response_model=List[StateHistoryResponse])
async def get_history_by_stage(
    stage_run_id: int,
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить историю переходов для конкретного этапа."""
    return await state_history_service.get_history_by_stage_run(
        db, stage_run_id, skip=skip, limit=limit
    )


@router.get("/", response_model=List[StateHistoryResponse])
async def get_all_history(
    skip: int = Query(0, description="Количество записей для пропуска"),
    limit: int = Query(100, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить всю историю переходов."""
    return await state_history_service.get_all_history(db, skip=skip, limit=limit)