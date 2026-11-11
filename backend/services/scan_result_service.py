from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..models.scan_result import ScanResult
from ..schemas.scan_result import ScanResultCreate, ScanResultResponse


async def create_scan_result(
    db: AsyncSession,
    result_data: ScanResultCreate
) -> ScanResult:
    """Создаёт результат сканирования."""
    scan_result = ScanResult(**result_data.model_dump())
    db.add(scan_result)
    await db.flush()
    await db.refresh(scan_result)
    return scan_result


async def get_scan_result(db: AsyncSession, result_id: int) -> ScanResult:
    """Получает результат по ID."""
    result = await db.execute(select(ScanResult).where(ScanResult.id == result_id))
    scan_result = result.scalars().first()
    
    if not scan_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Результат сканирования не найден"
        )
    
    return scan_result


async def get_results_by_process_run(
    db: AsyncSession,
    process_run_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[ScanResult]:
    """Получает результаты сканирования для конкретной сессии."""
    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.process_run_id == process_run_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_results_by_host(
    db: AsyncSession,
    host_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[ScanResult]:
    """Получает результаты сканирования для конкретного хоста."""
    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.host_id == host_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def delete_scan_result(db: AsyncSession, result_id: int) -> None:
    """Удаляет результат сканирования."""
    scan_result = await get_scan_result(db, result_id)
    await db.delete(scan_result)
    await db.flush()