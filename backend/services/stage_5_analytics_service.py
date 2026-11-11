import os
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict
from ..models.stage_run import StageRun
from ..models.process_run import ProcessRun
from ..models.host import Host
from ..models.scan_result import ScanResult
from ..models.process_log import ProcessLog
from ..models.report import ReportTemplate, AnalyticsReport


# ============================================================
# КОНСТАНТЫ
# ============================================================

REPORTS_DIR = Path("./analytics_reports")

OUTPUT_ANALYTICS_GENERATED = "ANALYTICS_GENERATED"
OUTPUT_FAILED = "FAILED"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _ensure_reports_dir():
    """Создаёт папку для аналитических отчётов."""
    REPORTS_DIR.mkdir(exist_ok=True)


async def _collect_analytics_data(
    db: AsyncSession,
    stage_run: StageRun
) -> Dict:
    """
    Собрать данные для аналитического отчёта из БД.
    
    Включает:
    - Общая информация о сессии (дата, группа, количество хостов)
    - Статистика по уязвимостям (критические/высокие/средние/низкие)
    - Топ хостов по количеству уязвимостей
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        Словарь с данными для отчёта
    """
    process_run_result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == stage_run.process_run_id)
    )
    process_run = process_run_result.scalars().first()
    
    # Количество хостов
    hosts_count_result = await db.execute(
        select(func.count(Host.id)).where(Host.group_id == process_run.group_id)
    )
    hosts_count = hosts_count_result.scalar()
    
    # Статистика по уязвимостям
    stats_result = await db.execute(
        select(
            func.sum(ScanResult.critical_severity_count),
            func.sum(ScanResult.high_severity_count),
            func.sum(ScanResult.medium_severity_count),
            func.sum(ScanResult.low_severity_count)
        ).where(ScanResult.process_run_id == stage_run.process_run_id)
    )
    stats = stats_result.first()
    
    # Топ хостов по уязвимостям
    top_hosts_result = await db.execute(
        select(
            ScanResult.host_connection_address,
            (ScanResult.critical_severity_count + ScanResult.high_severity_count +
             ScanResult.medium_severity_count + ScanResult.low_severity_count).label('total')
        )
        .where(ScanResult.process_run_id == stage_run.process_run_id)
        .order_by(func.coalesce(
            ScanResult.critical_severity_count + ScanResult.high_severity_count +
            ScanResult.medium_severity_count + ScanResult.low_severity_count, 0
        ).desc())
        .limit(10)
    )
    top_hosts = top_hosts_result.all()
    
    return {
        "process_run_id": process_run.id,
        "group_id": process_run.group_id,
        "started_at": process_run.started_at,
        "ended_at": process_run.ended_at,
        "hosts_count": hosts_count,
        "critical_count": stats[0] or 0,
        "high_count": stats[1] or 0,
        "medium_count": stats[2] or 0,
        "low_count": stats[3] or 0,
        "top_hosts": [
            {"address": row[0], "total_vulns": row[1] or 0}
            for row in top_hosts
        ]
    }


async def _get_template(db: AsyncSession, format: str) -> ReportTemplate | None:
    """Получить шаблон отчёта по формату."""
    result = await db.execute(
        select(ReportTemplate)
        .where(ReportTemplate.format == format)
        .order_by(ReportTemplate.created_at.desc())
    )
    return result.scalars().first()


async def _generate_pdf_report(data: Dict, template: ReportTemplate) -> bytes:
    """
    Сгенерировать PDF-отчёт.
    
    В production использовать библиотеку reportlab или weasyprint.
    Сейчас: заглушка, возвращающая минимальный PDF.
    """
    # TODO: Реализовать генерацию PDF на основе template и data
    return b"%PDF-1.4 stub"


async def _generate_csv_report(data: Dict, template: ReportTemplate) -> bytes:
    """
    Сгенерировать CSV-отчёт.
    
    В production использовать csv модуль.
    Сейчас: заглушка.
    """
    # TODO: Реализовать генерацию CSV
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Hosts Count", data["hosts_count"]])
    writer.writerow(["Critical", data["critical_count"]])
    writer.writerow(["High", data["high_count"]])
    writer.writerow(["Medium", data["medium_count"]])
    writer.writerow(["Low", data["low_count"]])
    
    return output.getvalue().encode('utf-8')


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

async def execute(db: AsyncSession, stage_run: StageRun) -> str:
    """
    Логика этапа 5: Формирование аналитики.
    
    Подэтапы:
    1. Собрать данные из БД (scan_result, process_run, host, group)
    2. Загрузить шаблон отчёта (report_template)
    3. Сгенерировать отчёт (PDF + CSV)
    4. Сохранить файлы
    5. Сохранить метаданные в таблицу analytics_report
    6. Вернуть stage_output_status: ANALYTICS_GENERATED или FAILED
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        stage_output_status
    """
    try:
        # Подэтап 1: Собираем данные
        data = await _collect_analytics_data(db, stage_run)
        
        # Подэтап 2: Получаем шаблон
        template = await _get_template(db, "PDF")
        
        # Подэтап 3-4: Генерируем и сохраняем PDF
        _ensure_reports_dir()
        
        pdf_content = await _generate_pdf_report(data, template)
        pdf_filename = f"analytics_{stage_run.process_run_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = REPORTS_DIR / pdf_filename
        pdf_path.write_bytes(pdf_content)
        
        # Генерируем и сохраняем CSV
        csv_content = await _generate_csv_report(data, template)
        csv_filename = pdf_filename.replace('.pdf', '.csv')
        csv_path = REPORTS_DIR / csv_filename
        csv_path.write_bytes(csv_content)
        
        # Подэтап 5: Сохраняем метаданные в таблицу analytics_report
        analytics_report = AnalyticsReport(
            process_run_id=stage_run.process_run_id,
            template_id=template.id if template else None,
            report_type="PDF",
            file_path=str(pdf_path),
            generated_at=datetime.utcnow(),
            generation_status="SUCCESS"
        )
        db.add(analytics_report)
        
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="INFO",
            message=f"Аналитический отчёт сформирован: {pdf_filename}, {csv_filename}"
        )
        db.add(process_log)
        
        return OUTPUT_ANALYTICS_GENERATED
    
    except Exception as e:
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="CRITICAL",
            message=f"Ошибка выполнения этапа 5: {str(e)}"
        )
        db.add(process_log)
        return OUTPUT_FAILED