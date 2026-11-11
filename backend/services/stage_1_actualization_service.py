from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Tuple
from ..models.stage_run import StageRun
from ..models.process_run import ProcessRun
from ..models.host import Host
from ..models.job import Job
from ..models.process_log import ProcessLog
from ..services import state_history_service
from ..services import redcheck_client


# ============================================================
# КОНСТАНТЫ
# ============================================================

SCAN_TYPE_HOST_DISCOVERY = 24

OUTPUT_SUCCESS = "SUCCESS"
OUTPUT_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
OUTPUT_FAILED = "FAILED"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def _get_process_run(db: AsyncSession, stage_run: StageRun) -> ProcessRun:
    """Получает сессию, к которой относится этап."""
    result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == stage_run.process_run_id)
    )
    return result.scalars().first()


async def _get_redcheck_group_info(db: AsyncSession, group_id: int) -> Tuple[int | None, str | None]:
    """
    Получить ID и название группы в RedCheck.
    
    Берёт из таблицы job (поле groups_data).
    
    Args:
        db: Сессия базы данных
        group_id: ID группы в БД комплекса
    
    Returns:
        (redcheck_group_id, group_name) или (None, None)
    """
    result = await db.execute(
        select(Job).where(Job.is_deleted_in_redcheck == False)
    )
    jobs = result.scalars().all()
    
    for job in jobs:
        if job.groups_data:
            for group_info in job.groups_data:
                if group_info.get('id') == group_id:
                    return group_info.get('id'), group_info.get('name', f"Group_{group_id}")
    
    return None, None


async def _get_current_hosts_from_redcheck(
    db: AsyncSession,
    stage_run: StageRun,
    redcheck_group_id: int
) -> List[Dict]:
    """
    Подэтап 1: Получить текущий список хостов из RedCheck.
    
    GET /api/v1.0/targets/hosts?GroupId={redcheck_group_id}
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
        redcheck_group_id: ID группы в RedCheck
    
    Returns:
        Список хостов в формате:
        [{"id": 1, "guid": "...", "connectionAddress": "192.168.1.10", ...}, ...]
    """
    token = await redcheck_client.authenticate("admin", "admin")
    return await redcheck_client.get_hosts_by_group(redcheck_group_id, token)


async def _run_host_discovery(db: AsyncSession, stage_run: StageRun) -> List[Dict]:
    """
    Подэтап 2: Запустить "Обнаружение хостов" и получить результат.
    
    В production:
    1. Найти задание с scan_type=20 для группы сессии
    2. Вызвать redcheck_client.run_job(job_id)
    3. Дождаться завершения (через polling)
    4. Получить список хостов, ответивших на ping
    
    Сейчас: заглушка, возвращающая тестовые данные.
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        Список обнаруженных хостов:
        [{"connectionAddress": "192.168.1.100", "guid": "..."}, ...]
    """
    # TODO: Реализовать через redcheck_client
    # process_run = await _get_process_run(db, stage_run)
    # job_id = await _find_redcheck_job_id(db, process_run.group_id, SCAN_TYPE_HOST_DISCOVERY)
    # scan_result = await redcheck_client.run_and_get_scan_result(job_id)
    # return scan_result["hosts"]
    
    # Заглушка: возвращаем тестовые данные
    # Включает один новый хост (192.168.1.100), которого нет в текущем списке
    return [
        {"connectionAddress": "192.168.1.10", "guid": "guid-1"},
        {"connectionAddress": "192.168.1.11", "guid": "guid-2"},
        {"connectionAddress": "192.168.1.100", "guid": "guid-new"}  # Новый хост
    ]


def _compare_host_lists(
    current_redcheck_hosts: List[Dict],
    discovered_hosts: List[Dict]
) -> Tuple[List[Dict], List[Dict]]:
    """
    Подэтап 3: Сравнить два списка хостов.
    
    Логика:
    - Новые хосты: есть в discovered, но нет в current → нужно добавить в RedCheck
    - Устаревшие хосты: есть в current, но нет в discovered → нужно удалить из RedCheck
    
    Args:
        current_redcheck_hosts: Текущий список хостов в RedCheck
        discovered_hosts: Хосты, обнаруженные заданием "Обнаружение хостов"
    
    Returns:
        Кортеж (new_hosts, stale_hosts):
        - new_hosts: список новых хостов для импорта
        - stale_hosts: список устаревших хостов для удаления
    """
    current_ips = {h.get('connectionAddress') for h in current_redcheck_hosts if h.get('connectionAddress')}
    discovered_ips = {h.get('connectionAddress') for h in discovered_hosts if h.get('connectionAddress')}
    
    new_hosts = [h for h in discovered_hosts if h.get('connectionAddress') not in current_ips]
    stale_hosts = [h for h in current_redcheck_hosts if h.get('connectionAddress') not in discovered_ips]
    
    return new_hosts, stale_hosts


async def _import_new_hosts_to_redcheck(
    db: AsyncSession,
    stage_run: StageRun,
    new_hosts: List[Dict],
    redcheck_group_id: int,
    group_name: str
) -> int:
    """
    Подэтап 4a: Автоматически импортировать новые хосты в RedCheck через CSV.
    
    Логика:
    1. Создать CSV-файл с новыми хостами (формат: Group,Host,HostDesc)
    2. Импортировать CSV в RedCheck через POST /api/v1.0/targets/hosts/import/csv
    3. Записать результат в process_log
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
        new_hosts: Список новых хостов для импорта
        redcheck_group_id: ID группы в RedCheck
        group_name: Название группы в RedCheck
    
    Returns:
        Количество успешно импортированных хостов
    """
    if not new_hosts:
        return 0
    
    # Создаём CSV-содержимое
    csv_content = redcheck_client.create_hosts_csv(new_hosts, group_name)
    
    # Импортируем в RedCheck
    token = await redcheck_client.authenticate("admin", "admin")
    result = await redcheck_client.import_hosts_csv(redcheck_group_id, csv_content, token)
    
    imported_count = result.get("hostCreated", 0)
    
    # Запись в process_log
    process_log = ProcessLog(
        process_run_id=stage_run.process_run_id,
        stage_run_id=stage_run.id,
        log_level="INFO",
        message=(
            f"Автоматически импортировано {imported_count} новых хостов в RedCheck. "
            f"IP-адреса: {', '.join(h.get('connectionAddress', '') for h in new_hosts)}"
        )
    )
    db.add(process_log)
    
    return imported_count


async def _handle_stale_hosts(
    db: AsyncSession,
    stage_run: StageRun,
    stale_hosts: List[Dict]
) -> Tuple[bool, List[Dict]]:
    """
    Подэтап 4b: Обработка устаревших хостов.
    
    Если есть устаревшие хосты — возвращаем флаг HOLD и список хостов.
    Пользователь должен подтвердить удаление через approve/reject (две фазы).
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
        stale_hosts: Список устаревших хостов из RedCheck
    
    Returns:
        Кортеж (needs_hold, stale_hosts):
        - needs_hold: True, если есть хосты для удаления
        - stale_hosts: тот же список (для сохранения в hold_data)
    """
    if not stale_hosts:
        return False, []
    
    # Запись в process_log
    process_log = ProcessLog(
        process_run_id=stage_run.process_run_id,
        stage_run_id=stage_run.id,
        log_level="WARNING",
        message=(
            f"Обнаружено {len(stale_hosts)} устаревших хостов в RedCheck: "
            f"{', '.join(h.get('connectionAddress', '') for h in stale_hosts)}. "
            f"Требуется подтверждение пользователя для удаления."
        )
    )
    db.add(process_log)
    
    return True, stale_hosts


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ ВЫПОЛНЕНИЯ ЭТАПА
# ============================================================

async def execute(db: AsyncSession, stage_run: StageRun) -> str:
    """
    Логика этапа 1: Актуализация объектов в RedCheck.
    
    Подэтапы:
    1. Получить текущий список хостов из RedCheck
       (GET /api/v1.0/targets/hosts?GroupId={group_id})
    2. Запустить "Обнаружение хостов" (scan_type=20) в RedCheck
    3. Сравнить оба списка
    4a. Новые хосты → создать CSV → импорт в RedCheck (автоматически)
    4b. Устаревшие хосты → HOLD (фаза 1: RedCheck, фаза 2: БД)
    
    Args:
        db: Сессия базы данных
        stage_run: Объект этапа
    
    Returns:
        stage_output_status:
        - "SUCCESS" — все хосты актуальны, новых и устаревших нет
        - "PARTIAL_SUCCESS" — есть расхождения (новые импортированы,
          устаревшие требуют подтверждения через HOLD)
        - "FAILED" — ошибка выполнения (например, группа не найдена)
    """
    try:
        # Получаем сессию для доступа к group_id
        process_run = await _get_process_run(db, stage_run)
        if not process_run:
            return OUTPUT_FAILED
        
        # Получаем ID и название группы в RedCheck
        redcheck_group_id, group_name = await _get_redcheck_group_info(
            db, process_run.group_id
        )
        if not redcheck_group_id:
            process_log = ProcessLog(
                process_run_id=stage_run.process_run_id,
                stage_run_id=stage_run.id,
                log_level="CRITICAL",
                message=f"Группа {process_run.group_id} не найдена в RedCheck"
            )
            db.add(process_log)
            return OUTPUT_FAILED
        
        # Подэтап 1: Получаем текущий список хостов из RedCheck
        current_hosts = await _get_current_hosts_from_redcheck(
            db, stage_run, redcheck_group_id
        )
        
        # Подэтап 2: Запускаем обнаружение хостов
        discovered_hosts = await _run_host_discovery(db, stage_run)
        
        # Подэтап 3: Сравниваем списки
        new_hosts, stale_hosts = _compare_host_lists(current_hosts, discovered_hosts)
        
        # Подэтап 4a: Импортируем новые хосты в RedCheck
        imported_count = await _import_new_hosts_to_redcheck(
            db, stage_run, new_hosts, redcheck_group_id, group_name
        )
        
        # Подэтап 4b: Проверяем наличие устаревших хостов
        needs_hold, stale_hosts_list = await _handle_stale_hosts(
            db, stage_run, stale_hosts
        )
        
        if needs_hold:
            # Сохраняем контекст HOLD в stage_run.hold_data
            # Фаза REDCHECK: сначала удаляем из RedCheck, потом из БД
            stage_run.hold_data = {
                "phase": "REDCHECK",
                "hosts_to_delete": [
                    {
                        "redcheck_id": h.get("id"),
                        "guid": h.get("guid"),
                        "connection_address": h.get("connectionAddress"),
                        "description": h.get("description", "")
                    }
                    for h in stale_hosts_list
                ]
            }
            return OUTPUT_PARTIAL_SUCCESS
        elif imported_count > 0 or len(discovered_hosts) > 0:
            return OUTPUT_SUCCESS
        else:
            return OUTPUT_FAILED
    
    except Exception as e:
        process_log = ProcessLog(
            process_run_id=stage_run.process_run_id,
            stage_run_id=stage_run.id,
            log_level="CRITICAL",
            message=f"Ошибка выполнения этапа 1: {str(e)}"
        )
        db.add(process_log)
        return OUTPUT_FAILED