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

SCAN_TYPE_VULNERABILITY_AUDIT = 5

OUTPUT_ALL_SCANNED = "ALL_SCANNED"
OUTPUT_PARTIAL_SCANNED = "PARTIAL_SCANNED"
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


async def _run_vulnerability_audit(
    db: AsyncSession,
    stage_run: StageRun,
    hosts: List[Host]
) -> dict:
    """
    Запустить задание "Аудит уязвимостей" в RedCheck и получить результат.
    
    В production:
    1. Найти задание с scan_type=5
    2. Вызвать redcheck_client.run_job(job_id)
    3. Дождаться завершения
    4. Вернуть словарь {host_address: {low, medium, high, critical}}
    
    Сейчас: заглушка.
    
    Returns:
        Словарь {connection_address: {low_severity_count, medium_severity_count,
                                      high_severity_count, critical_severity_count}}
    """
    # TODO: Реализовать через redcheck_client
    return {}


async def _save_audit_results(
    db: AsyncSession,
    stage_run: StageRun,
    audit_results: dict
) -> tuple:
    """
    Сохранить результаты аудита уязвимостей в scan_result.
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
        audit_results: Словарь с результатами сканирования
    
    Returns:
        (scanned_count, total_count)
    """
    scanned_count = 0
    total_count = len(audit_results)
    
    for host_address, vuln_data in audit_results.items():
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
                is_accessible=True,
                low_severity_count=vuln_data.get('low', 0),
                medium_severity_count=vuln_data.get('medium', 0),
                high_severity_count=vuln_data.get('high', 0),
                critical_severity_count=vuln_data.get('critical', 0)
            )
            db.add(scan_result)
        else:
            scan_result.low_severity_count = vuln_data.get('low', 0)
            scan_result.medium_severity_count = vuln_data.get('medium', 0)
            scan_result.high_severity_count = vuln_data.get('high', 0)
            scan_result.critical_severity_count = vuln_data.get('critical', 0)
        
        scanned_count += 1
    
    return scanned_count, total_count


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

async def execute(db: AsyncSession, stage_run: StageRun) -> str:
    """
    Логика этапа 3: Аудит уязвимостей.
    
    Подэтапы:
    1. Получить список хостов группы
    2. Запустить задание "Аудит уязвимостей" (scan_type=5) в RedCheck
    3. Получить результаты сканирования
    4. Сохранить результаты в scan_result
    5. Вернуть stage_output_status:
       - ALL_SCANNED — все хосты просканированы
       - PARTIAL_SCANNED — частично просканированы
       - FAILED — ошибка выполнения
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        stage_output_status
    """
    try:
        hosts = await _get_hosts_for_stage(db, stage_run)
        if not hosts:
            return OUTPUT_FAILED
        
        audit_results = await _run_vulnerability_audit(db, stage_run, hosts)
        
        if not audit_results:
            return OUTPUT_FAILED
        
        scanned_count, total_count = await _save_audit_results(
            db, stage_run, audit_results
        )
        
        if scanned_count == total_count:
            return OUTPUT_ALL_SCANNED
        elif scanned_count > 0:
            return OUTPUT_PARTIAL_SCANNED
        else:
            return OUTPUT_FAILED
    
    except Exception as e:
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="CRITICAL",
            message=f"Ошибка выполнения этапа 3: {str(e)}"
        )
        db.add(process_log)
        return OUTPUT_FAILED