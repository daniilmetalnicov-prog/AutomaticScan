import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.stage_run import StageRun
from ..models.process_run import ProcessRun
from ..models.report import Report
from ..models.process_log import ProcessLog
from ..models.system_config import SystemConfig


# ============================================================
# КОНСТАНТЫ
# ============================================================

TEMP_REPORTS_DIR = Path("./temp_reports")
REPORT_FORMAT = "pdf"

OUTPUT_REPORTS_PLACED = "REPORTS_PLACED"
OUTPUT_FAILED = "FAILED"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _ensure_temp_dir():
    """Создаёт временную папку для отчётов, если её нет."""
    TEMP_REPORTS_DIR.mkdir(exist_ok=True)


async def _get_network_path(db: AsyncSession) -> str:
    """Получает путь к сетевой папке из system_config."""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == 'reports_network_path')
    )
    config = result.scalars().first()
    return config.config_value if config else "./network_reports"


async def _get_scan_result_id(db: AsyncSession, stage_run: StageRun) -> str | None:
    """
    Подэтап 1: Получить ID результата сканирования из RedCheck.
    
    GET /api/v1.0/integration/jobs/scans?jobId={job_id}
    
    Returns:
        scan_result_id и дата завершения сканирования
    """
    # TODO: Реализовать через redcheck_client
    # response = await redcheck_client.get_scan_result(job_id)
    # return response['scanResultId'], response['completedAt']
    return None, None


async def _get_report_id(
    db: AsyncSession,
    scan_result_id: str,
    completed_at: str
) -> str | None:
    """
    Подэтап 2: Получить ID отчёта.
    
    GET /api/v1.0/reports?FromCreateDate={completed_at}
    
    Returns:
        report_id
    """
    # TODO: Реализовать через redcheck_client
    return None


async def _export_report(report_id: str, format: str = "pdf") -> str | None:
    """
    Подэтап 3: Сгенерировать файл отчёта.
    
    POST /api/v1.0/reports/export
    Body: {"reportId": report_id, "format": format}
    
    Returns:
        export_guid
    """
    # TODO: Реализовать через redcheck_client
    return None


async def _download_report(
    report_id: str,
    format: str,
    export_guid: str
) -> bytes | None:
    """
    Подэтап 4: Скачать файл отчёта.
    
    GET /api/v1.0/reports/downloadfile?reportId={report_id}&format={format}&exportGuid={export_guid}
    
    Returns:
        Содержимое файла (bytes)
    """
    # TODO: Реализовать через redcheck_client
    return None


def _calculate_file_hash(file_content: bytes) -> str:
    """Вычисляет SHA-256 хэш файла."""
    return hashlib.sha256(file_content).hexdigest()


async def _save_to_temp(file_content: bytes, filename: str) -> Path:
    """Сохраняет файл во временную папку."""
    _ensure_temp_dir()
    file_path = TEMP_REPORTS_DIR / filename
    file_path.write_bytes(file_content)
    return file_path


async def _move_to_network(
    temp_path: Path,
    network_path: str,
    filename: str
) -> Path:
    """Перемещает файл из временной папки в сетевую."""
    network_dir = Path(network_path)
    network_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = network_dir / filename
    shutil.move(str(temp_path), str(dest_path))
    return dest_path


async def _verify_integrity(
    file_path: Path,
    expected_hash: str
) -> bool:
    """Проверяет целостность файла по SHA-256."""
    file_content = file_path.read_bytes()
    actual_hash = _calculate_file_hash(file_content)
    return actual_hash == expected_hash


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

async def execute(db: AsyncSession, stage_run: StageRun) -> str:
    """
    Логика этапа 4: Размещение отчётов.
    
    Подэтапы:
    1. Получить ID результата сканирования из RedCheck
       (GET /api/v1.0/integration/jobs/scans)
    2. Получить ID отчёта
       (GET /api/v1.0/reports?FromCreateDate={completed_at})
    3. Сгенерировать файл отчёта
       (POST /api/v1.0/reports/export)
    4. Скачать файл
       (GET /api/v1.0/reports/downloadfile)
    5. Сохранить во временную папку ./temp_reports/
    6. Вычислить SHA-256 хэш
    7. Переместить в сетевую папку (путь из system_config)
    8. Проверить целостность (сравнить хэш)
    9. Сохранить метаданные в таблицу report
    10. Вернуть stage_output_status: REPORTS_PLACED или FAILED
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        stage_output_status
    """
    try:
        # Подэтап 1: Получаем ID результата сканирования
        scan_result_id, completed_at = await _get_scan_result_id(db, stage_run)
        if not scan_result_id:
            return OUTPUT_FAILED
        
        # Подэтап 2: Получаем ID отчёта
        report_id = await _get_report_id(db, scan_result_id, completed_at)
        if not report_id:
            return OUTPUT_FAILED
        
        # Подэтап 3: Генерируем файл отчёта
        export_guid = await _export_report(report_id, REPORT_FORMAT)
        if not export_guid:
            return OUTPUT_FAILED
        
        # Подэтап 4: Скачиваем файл
        file_content = await _download_report(report_id, REPORT_FORMAT, export_guid)
        if not file_content:
            return OUTPUT_FAILED
        
        # Подэтап 5: Сохраняем во временную папку
        filename = f"report_{stage_run.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        temp_path = await _save_to_temp(file_content, filename)
        
        # Подэтап 6: Вычисляем хэш
        file_hash = _calculate_file_hash(file_content)
        
        # Подэтап 7: Перемещаем в сетевую папку
        network_path = await _get_network_path(db)
        network_file_path = await _move_to_network(temp_path, network_path, filename)
        
        # Подэтап 8: Проверяем целостность
        is_valid = await _verify_integrity(network_file_path, file_hash)
        if not is_valid:
            process_log = ProcessLog(
                process_run_id=stage_run.process_run_id,
                stage_run_id=stage_run.id,
                log_level="CRITICAL",
                message=f"Нарушение целостности файла отчёта: {filename}"
            )
            db.add(process_log)
            return OUTPUT_FAILED
        
        # Подэтап 9: Сохраняем метаданные в таблицу report
        report = Report(
            stage_run_id=stage_run.id,
            file_path=str(network_file_path),
            file_hash=file_hash,
            network_path=str(network_file_path),
            placed_at=datetime.utcnow(),
            placement_status="SUCCESS"
        )
        db.add(report)
        
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="INFO",
            message=f"Отчёт успешно размещён: {filename} (хэш: {file_hash[:16]}...)"
        )
        db.add(process_log)
        
        return OUTPUT_REPORTS_PLACED
    
    except Exception as e:
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="CRITICAL",
            message=f"Ошибка выполнения этапа 4: {str(e)}"
        )
        db.add(process_log)
        return OUTPUT_FAILED