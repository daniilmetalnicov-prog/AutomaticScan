from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..core.database import get_db
from ..schemas.process_run import ProcessRunResponse
from ..services import health_service

router = APIRouter(prefix="/api/health", tags=["Здоровье системы"])


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Проверка общего состояния системы.
    
    Возвращает:
    - status: "healthy" / "degraded" / "unhealthy"
    - active_sessions: количество активных сессий
    - stuck_sessions: количество зависших сессий
    - db_status: статус базы данных
    """
    return await health_service.get_system_health(db)


@router.get("/stuck-sessions")
async def get_stuck_sessions(db: AsyncSession = Depends(get_db)):
    """Получить список зависших сессий."""
    sessions = await health_service.find_stuck_sessions(db)
    return [
        {
            "id": s.id,
            "status": s.status,
            "started_at": s.started_at,
            "group_id": s.group_id
        }
        for s in sessions
    ]


@router.post("/reset-stuck-sessions")
async def reset_stuck_sessions(
    auto: bool = Query(False, description="Автоматический сброс (без записи в audit_log)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Сбросить все зависшие сессии в статус FAILED.
    
    Используется для очистки системы от зависших сессий.
    Можно вызывать вручную или настроить cron-задачу.
    """
    reset_ids = await health_service.reset_stuck_sessions(db, auto=auto)
    return {"reset_count": len(reset_ids), "reset_ids": reset_ids}


@router.post("/process-runs/{process_run_id}/command-reset", response_model=ProcessRunResponse)
async def command_reset(
    process_run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Принудительный сброс сессии (Command_Reset).
    
    Используется в критических ситуациях, когда обычный reset не помогает.
    Очищает все связанные ресурсы и возвращает сессию в IDLE.
    """
    return await health_service.command_reset(db, process_run_id)