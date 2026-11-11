from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..models.stage_run import StageRun
from ..models.process_run import ProcessRun
from ..models.host import Host
from ..models.job import Job
from ..models.scan_result import ScanResult
from ..models.process_log import ProcessLog


# ============================================================
# КОНСТАНТЫ
# ============================================================

SCAN_TYPE_AVAILABILITY_CHECK = 20

OUTPUT_ALL_ACCESSIBLE = "ALL_ACCESSIBLE"
OUTPUT_PARTIAL_ACCESSIBLE = "PARTIAL_ACCESSIBLE"
OUTPUT_ZERO_ACCESSIBLE = "ZERO_ACCESSIBLE"
OUTPUT_FAILED = "FAILED"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def _get_hosts_for_stage(db: AsyncSession, stage_run: StageRun) -> List[Host]:
    """Получает все хосты группы сессии."""
    process_run_result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == stage_run.process_run_id)
    )
    process_run = process_run_result.scalars().first()
    
    if not process_run:
        return []
    
    result = await db.execute(
        select(Host).where(Host.group_id == process_run.group_id)
    )
    return result.scalars().all()


async def _check_availability_in_redcheck(
    db: AsyncSession,
    stage_run: StageRun,
    hosts: List[Host]
) -> dict:
    """
    Запустить задание "Проверка доступности" в RedCheck и получить результат.
    
    В production:
    1. Найти задание с scan_type=20
    2. Вызвать redcheck_client.run_job(job_id)
    3. Дождаться завершения
    4. Вернуть словарь {host_id: is_accessible}
    
    Сейчас: заглушка.
    
    Returns:
        Словарь {connection_address: is_accessible}
    """
    # TODO: Реализовать через redcheck_client
    # job_id = await _find_redcheck_job_id(db, process_run.group_id, SCAN_TYPE_AVAILABILITY_CHECK)
    # results = await redcheck_client.run_and_get_availability(job_id)
    # return results
    
    return {}


async def _save_availability_results(
    db: AsyncSession,
    stage_run: StageRun,
    availability_results: dict
) -> tuple:
    """
    Сохранить результаты проверки доступности в scan_result.
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
        availability_results: Словарь {connection_address: is_accessible}
    
    Returns:
        (accessible_count, total_count)
    """
    accessible_count = 0
    total_count = len(availability_results)
    
    for host_address, is_accessible in availability_results.items():
        # Ищем или создаём scan_result для хоста
        result = await db.execute(
            select(ScanResult).where(
                ScanResult.process_run_id == stage_run.process_run_id,
                ScanResult.host_connection_address == host_address
            )
        )
        scan_result = result.scalars().first()
        
        if not scan_result:
            scan_result = ScanResult(
                process_run_id=stage_run.process_run_id,
                host_connection_address=host_address,
                is_accessible=is_accessible
            )
            db.add(scan_result)
        else:
            scan_result.is_accessible = is_accessible
        
        if is_accessible:
            accessible_count += 1
    
    return accessible_count, total_count


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

async def execute(db: AsyncSession, stage_run: StageRun) -> str:
    """
    Логика этапа 2: Проверка доступности.
    
    Подэтапы:
    1. Получить список хостов группы
    2. Запустить задание "Проверка доступности" (scan_type=20) в RedCheck
    3. Получить результат (какие хосты доступны)
    4. Сохранить результаты в scan_result (is_accessible)
    5. Вернуть stage_output_status:
       - ALL_ACCESSIBLE — все хосты доступны
       - PARTIAL_ACCESSIBLE — частично доступны
       - ZERO_ACCESSIBLE — ни один не доступен
       - FAILED — ошибка выполнения
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        stage_output_status
    """
    try:
        # Получаем хосты
        hosts = await _get_hosts_for_stage(db, stage_run)
        if not hosts:
            return OUTPUT_FAILED
        
        # Запускаем проверку доступности в RedCheck
        availability_results = await _check_availability_in_redcheck(
            db, stage_run, hosts
        )
        
        if not availability_results:
            return OUTPUT_FAILED
        
        # Сохраняем результаты
        accessible_count, total_count = await _save_availability_results(
            db, stage_run, availability_results
        )
        
        # Определяем статус
        if accessible_count == total_count:
            return OUTPUT_ALL_ACCESSIBLE
        elif accessible_count > 0:
            return OUTPUT_PARTIAL_ACCESSIBLE
        else:
            return OUTPUT_ZERO_ACCESSIBLE
    
    except Exception as e:
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="CRITICAL",
            message=f"Ошибка выполнения этапа 2: {str(e)}"
        )
        db.add(process_log)
        return OUTPUT_FAILED