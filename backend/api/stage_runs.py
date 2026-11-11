from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.stage_run import StageRunResponse
from ..services import stage_run_service
from ..services import stage_run_orchestrator

router = APIRouter(prefix="/api/stage-runs", tags=["Этапы сканирования"])


# ============================================================
# ВАЖНО: порядок маршрутов критичен для FastAPI!
# Конкретные маршруты должны идти ПЕРЕД маршрутами с параметрами
# ============================================================


# --- УПРАВЛЕНИЕ (конкретные маршруты) ---

@router.post("/{stage_run_id}/execute", response_model=StageRunResponse)
async def execute_stage_endpoint(
    stage_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Запустить выполнение этапа.
    
    Оркестратор делегирует выполнение специализированному сервису
    (stage_1, stage_2, и т.д.), который выполняет реальную работу
    и возвращает stage_output_status. Затем автоматически вызывается DMN.
    
    Примеры:
    - Этап 1 (Актуализация): возвращает SUCCESS/PARTIAL_SUCCESS/FAILED
    - Этап 2 (Доступность): возвращает ALL_ACCESSIBLE/PARTIAL_ACCESSIBLE/ZERO_ACCESSIBLE/FAILED
    - Этап 3 (Аудит): возвращает ALL_SCANNED/PARTIAL_SCANNED/FAILED
    - Этап 4 (Отчёты): возвращает REPORTS_PLACED/FAILED
    - Этап 5 (Аналитика): возвращает ANALYTICS_GENERATED/FAILED
    """
    return await stage_run_orchestrator.execute_stage(db, stage_run_id)


@router.post("/{stage_run_id}/complete-with-dmn", response_model=StageRunResponse)
async def complete_stage_with_dmn_endpoint(
    stage_run_id: int,
    stage_output_status: str = Query(
        ..., 
        description="Результат выполнения этапа (SUCCESS, FAILED, PARTIAL_SUCCESS и т.д.)"
    ),
    triggered_by: str = Query("system", description="Кто инициировал завершение"),
    db: AsyncSession = Depends(get_db)
):
    """
    ВРЕМЕННЫЙ ЭНДПОИНТ ДЛЯ ТЕСТИРОВАНИЯ!
    
    Завершает этап с автоматическим вызовом DMN.
    
    В production эту логику будет вызывать polling-менеджер после получения
    результата от RedCheck API.
    
    Примеры stage_output_status:
    - SUCCESS, PARTIAL_SUCCESS, FAILED (для Актуализации объектов)
    - ALL_ACCESSIBLE, PARTIAL_ACCESSIBLE, ZERO_ACCESSIBLE, FAILED (для Проверки доступности)
    - ALL_SCANNED, PARTIAL_SCANNED, FAILED (для Аудита уязвимостей)
    - REPORTS_PLACED, FAILED (для Размещения отчётов)
    - ANALYTICS_GENERATED, FAILED (для Формирования аналитики)
    """
    return await stage_run_service.complete_stage_with_dmn(
        db, stage_run_id, stage_output_status, triggered_by
    )


@router.post("/{stage_run_id}/approve", response_model=StageRunResponse)
async def approve_stage(
    stage_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """
    Подтвердить действие на этапе (только для этапа в статусе HOLD).
    
    Переводит этап в SUCCESS и запускает следующий этап.
    """
    return await stage_run_service.approve_stage(db, stage_run_id, user_login)


@router.post("/{stage_run_id}/reject", response_model=StageRunResponse)
async def reject_stage(
    stage_run_id: int,
    user_login: str = Query("anonymous", description="Логин пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """
    Отклонить действие на этапе (только для этапа в статусе HOLD).
    
    Переводит этап в SUCCESS (с другим stage_output_status) и запускает следующий этап.
    """
    return await stage_run_service.reject_stage(db, stage_run_id, user_login)


# --- ЧТЕНИЕ ---

@router.get("/process/{process_run_id}", response_model=List[StageRunResponse])
async def get_stages_by_process(
    process_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить все этапы сессии сканирования."""
    return await stage_run_service.get_stages_by_process_run(db, process_run_id)


@router.get("/{stage_run_id}", response_model=StageRunResponse)
async def get_stage_run(
    stage_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить этап по ID."""
    return await stage_run_service.get_stage_run(db, stage_run_id)