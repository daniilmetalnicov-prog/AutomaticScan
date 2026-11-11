from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..models.process_log import ProcessLog
from ..models.stage_run import StageRun
from ..schemas.process_log import ProcessLogCreate


async def create_process_log(
    db: AsyncSession,
    log_data: ProcessLogCreate
) -> ProcessLog:
    """Создаёт запись лога процесса."""
    process_log = ProcessLog(**log_data.model_dump())
    db.add(process_log)
    await db.flush()
    await db.refresh(process_log)
    return process_log


async def get_logs_by_stage(
    db: AsyncSession,
    stage_run_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[ProcessLog]:
    """Получает логи для конкретного этапа."""
    result = await db.execute(
        select(ProcessLog)
        .where(ProcessLog.stage_run_id == stage_run_id)
        .order_by(ProcessLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_logs_by_process_run(
    db: AsyncSession,
    process_run_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[ProcessLog]:
    """
    Получает логи для конкретной сессии.
    
    Включает:
    - Логи, привязанные к сессии (process_run_id)
    - Логи, привязанные к этапам этой сессии (stage_run_id)
    """
    result = await db.execute(
        select(ProcessLog)
        .where(
            (ProcessLog.process_run_id == process_run_id) |
            (ProcessLog.stage_run_id.in_(
                select(StageRun.id).where(StageRun.process_run_id == process_run_id)
            ))
        )
        .order_by(ProcessLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_process_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[ProcessLog]:
    """Получает все логи процессов."""
    result = await db.execute(
        select(ProcessLog)
        .order_by(ProcessLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()