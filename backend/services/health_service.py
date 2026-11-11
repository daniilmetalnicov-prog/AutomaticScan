from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict
from ..models.system_config import SystemConfig
from ..models.process_run import ProcessRun
from ..models.stage_run import StageRun
from ..models.process_log import ProcessLog
from ..models.audit_log import AuditLog
from ..services import state_history_service


# ============================================================
# КОНСТАНТЫ
# ============================================================

# Ключи системных настроек (должны совпадать с записями в таблице system_config)
CONFIG_KEY_STUCK_TIMEOUT = 'stuck_session_timeout_hours'
CONFIG_KEY_POLLING_TIMEOUT = 'redcheck_polling_timeout_seconds'
CONFIG_KEY_MAX_RETRIES = 'max_retry_attempts'
CONFIG_KEY_HEALTH_INTERVAL = 'health_check_interval_minutes'
CONFIG_KEY_AUTO_RESET = 'auto_reset_stuck_sessions'

# Значения по умолчанию
DEFAULT_STUCK_TIMEOUT_HOURS = '24'
DEFAULT_POLLING_TIMEOUT_SECONDS = '300'
DEFAULT_MAX_RETRY_ATTEMPTS = '3'
DEFAULT_HEALTH_INTERVAL_MINUTES = '5'
DEFAULT_AUTO_RESET = 'true'


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def get_config_value(
    db: AsyncSession,
    key: str,
    default: str = None
) -> str | None:
    """
    Получает значение системной настройки из таблицы system_config.
    
    Логика:
    1. Ищет настройку по ключу config_key
    2. Если найдена — возвращает config_value
    3. Если не найдена — возвращает значение default
    
    Args:
        db: Сессия базы данных
        key: Ключ настройки (например, 'stuck_session_timeout_hours')
        default: Значение по умолчанию, если настройка не найдена
    
    Returns:
        Значение настройки (str) или default, если настройка не найдена
    """
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == key)
    )
    config = result.scalars().first()
    
    if config:
        return config.config_value
    
    return default


async def get_stuck_session_timeout_hours(db: AsyncSession) -> int:
    """
    Получает таймаут зависших сессий в часах.
    
    Значение хранится в таблице system_config под ключом
    'stuck_session_timeout_hours'. По умолчанию — 24 часа.
    
    Args:
        db: Сессия базы данных
    
    Returns:
        Таймаут в часах (int)
    """
    value = await get_config_value(db, CONFIG_KEY_STUCK_TIMEOUT, DEFAULT_STUCK_TIMEOUT_HOURS)
    return int(value)


async def is_auto_reset_enabled(db: AsyncSession) -> bool:
    """
    Проверяет, включён ли автоматический сброс зависших сессий.
    
    Значение хранится в таблице system_config под ключом
    'auto_reset_stuck_sessions'. По умолчанию — включено (true).
    
    Args:
        db: Сессия базы данных
    
    Returns:
        True, если автоматический сброс включён, иначе False
    """
    value = await get_config_value(db, CONFIG_KEY_AUTO_RESET, DEFAULT_AUTO_RESET)
    return value.lower() == 'true'


# ============================================================
# HEALTH CHECK — проверка общего состояния системы
# ============================================================

async def get_system_health(db: AsyncSession) -> Dict:
    """
    Проверяет общее состояние системы.
    
    Логика:
    1. Проверяет доступность БД (выполняет простой SELECT)
    2. Считает общее количество сессий
    3. Считает активные сессии (статус IN_PROGRESS)
    4. Считает зависшие сессии (IN_PROGRESS дольше установленного таймаута)
    5. Определяет статус системы:
       - healthy: нет зависших сессий
       - degraded: есть зависшие сессии
       - unhealthy: БД недоступна
    
    Args:
        db: Сессия базы данных
    
    Returns:
        Словарь с информацией о здоровье системы:
        - status: "healthy" / "degraded" / "unhealthy"
        - timestamp: время проверки (ISO 8601)
        - active_sessions: количество активных сессий
        - stuck_sessions: количество зависших сессий
        - total_sessions: общее количество сессий
        - stuck_session_timeout_hours: таймаут зависших сессий
        - db_status: "connected" / "disconnected"
        - error: текст ошибки (только при unhealthy)
    """
    try:
        # Проверяем доступность БД
        result = await db.execute(select(func.count(ProcessRun.id)))
        total_sessions = result.scalar()
        
        # Считаем активные сессии (IN_PROGRESS)
        result = await db.execute(
            select(func.count(ProcessRun.id)).where(ProcessRun.status == "IN_PROGRESS")
        )
        active_sessions = result.scalar()
        
        # Считаем зависшие сессии
        timeout_hours = await get_stuck_session_timeout_hours(db)
        threshold = datetime.utcnow() - timedelta(hours=timeout_hours)
        
        result = await db.execute(
            select(func.count(ProcessRun.id)).where(
                ProcessRun.status == "IN_PROGRESS",
                ProcessRun.started_at < threshold
            )
        )
        stuck_sessions = result.scalar()
        
        # Определяем статус системы
        if stuck_sessions > 0:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": active_sessions,
            "stuck_sessions": stuck_sessions,
            "total_sessions": total_sessions,
            "stuck_session_timeout_hours": timeout_hours,
            "db_status": "connected"
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "db_status": "disconnected"
        }


# ============================================================
# ПРОВЕРКА И СБРОС ЗАВИСШИХ СЕССИЙ
# ============================================================

async def find_stuck_sessions(db: AsyncSession) -> List[ProcessRun]:
    """
    Находит все зависшие сессии.
    
    Зависшей считается сессия, которая находится в статусе IN_PROGRESS
    дольше установленного таймаута (по умолчанию 24 часа).
    
    Args:
        db: Сессия базы данных
    
    Returns:
        Список зависших сессий ProcessRun
    """
    timeout_hours = await get_stuck_session_timeout_hours(db)
    threshold = datetime.utcnow() - timedelta(hours=timeout_hours)
    
    result = await db.execute(
        select(ProcessRun).where(
            ProcessRun.status == "IN_PROGRESS",
            ProcessRun.started_at < threshold
        )
    )
    return result.scalars().all()


async def reset_stuck_sessions(
    db: AsyncSession,
    auto: bool = False
) -> List[int]:
    """
    Сбрасывает все зависшие сессии в статус FAILED.
    
    Логика для каждой зависшей сессии:
    1. Переводит сессию в FAILED с описанием причины
    2. Записывает критическое событие в process_log (на уровне сессии)
    3. Записывает переход в state_history
    4. Для каждого незавершённого этапа:
       - Переводит в CANCELLED
       - Записывает событие в process_log (на уровне этапа)
       - Записывает переход в state_history
    5. Если auto=False — записывает событие в audit_log
    
    Args:
        db: Сессия базы данных
        auto: Если True — автоматический сброс (без записи в audit_log).
              Если False — ручной сброс (с записью в audit_log).
    
    Returns:
        Список ID сброшенных сессий
    """
    stuck_sessions = await find_stuck_sessions(db)
    reset_ids = []
    timeout_hours = await get_stuck_session_timeout_hours(db)
    
    for process_run in stuck_sessions:
        # Переводим сессию в FAILED
        process_run.status = "FAILED"
        process_run.ended_at = datetime.utcnow()
        process_run.error_message = (
            f"Сессия зависла в IN_PROGRESS более {timeout_hours} часов "
            f"и была автоматически сброшена"
        )
        
        # Запись в process_log (на уровне сессии)
        process_log = ProcessLog(
            process_run_id=process_run.id,
            stage_run_id=None,
            log_level="CRITICAL",
            message=(
                f"Сессия #{process_run.id} зависла в IN_PROGRESS и сброшена в FAILED. "
                f"Причина: превышен таймаут {timeout_hours} часов."
            )
        )
        db.add(process_log)
        
        # Запись в state_history
        await state_history_service.log_transition(
            db,
            process_run_id=process_run.id,
            entity_type="process_run",
            from_status="IN_PROGRESS",
            to_status="FAILED",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"Сессия зависла и сброшена (timeout > {timeout_hours}h)",
            triggered_by="system"
        )
        
        # Отменяем все незавершённые этапы
        result = await db.execute(
            select(StageRun).where(StageRun.process_run_id == process_run.id)
        )
        stages = result.scalars().all()
        
        for stage in stages:
            if stage.status in ["IDLE", "IN_PROGRESS", "HOLD"]:
                stage_from_status = stage.status
                stage.status = "CANCELLED"
                stage.ended_at = datetime.utcnow()
                
                # Запись в process_log (на уровне этапа)
                stage_process_log = ProcessLog(
                    process_run_id=process_run.id,
                    stage_run_id=stage.id,
                    log_level="CRITICAL",
                    message=(
                        f"Этап '{stage.current_stage}' отменён из-за зависания сессии #{process_run.id}. "
                        f"Предыдущий статус: {stage_from_status}."
                    )
                )
                db.add(stage_process_log)
                
                # Запись в state_history
                await state_history_service.log_transition(
                    db,
                    process_run_id=process_run.id,
                    entity_type="stage_run",
                    stage_run_id=stage.id,
                    from_status=stage_from_status,
                    to_status="CANCELLED",
                    transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                    reason=f"Этап '{stage.current_stage}' отменён из-за зависания сессии",
                    triggered_by="system"
                )
        
        # Запись в audit_log (только если не автоматический сброс)
        if not auto:
            audit_log = AuditLog(
                user_login="system",
                action_type="RESET_STUCK_SESSION",
                message=f"Сессия #{process_run.id} зависла и сброшена в FAILED"
            )
            db.add(audit_log)
        
        reset_ids.append(process_run.id)
    
    await db.flush()
    
    return reset_ids


# ============================================================
# COMMAND_RESET — принудительный сброс сессии
# ============================================================

async def command_reset(
    db: AsyncSession,
    process_run_id: int
) -> ProcessRun:
    """
    Принудительный сброс сессии (Command_Reset).
    
    Используется в критических ситуациях, когда обычный reset не помогает.
    Очищает все связанные ресурсы и возвращает сессию в IDLE.
    
    Отличия от обычного reset_process_run:
    - Сбрасывает сессии в ЛЮБОМ статусе (включая FAILED)
    - Записывает событие в process_log и audit_log как критическое
    - Предназначен для ручного вмешательства администратора
    
    Логика:
    1. Находит сессию по ID
    2. Сбрасывает статус сессии в IDLE
    3. Сбрасывает все этапы в IDLE
    4. Записывает событие в process_log
    5. Записывает событие в audit_log
    6. Записывает переход в state_history
    
    Args:
        db: Сессия базы данных
        process_run_id: ID сессии
    
    Returns:
        Сброшенная сессия ProcessRun
    
    Raises:
        HTTPException 404: Если сессия не найдена
    """
    from fastapi import HTTPException, status
    
    result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == process_run_id)
    )
    process_run = result.scalars().first()
    
    if not process_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
    
    from_status = process_run.status
    
    # Сбрасываем сессию
    process_run.status = "IDLE"
    process_run.started_at = None
    process_run.ended_at = None
    process_run.error_message = None
    
    # Сбрасываем все этапы
    result = await db.execute(
        select(StageRun).where(StageRun.process_run_id == process_run_id)
    )
    stages = result.scalars().all()
    
    for stage in stages:
        stage.status = "IDLE"
        stage.gate_decision = None
        stage.stage_output_status = None
        stage.started_at = None
        stage.ended_at = None
    
    # Запись в process_log
    process_log = ProcessLog(
        process_run_id=process_run_id,
        stage_run_id=None,
        log_level="CRITICAL",
        message=(
            f"Command_Reset выполнен для сессии #{process_run_id}. "
            f"Предыдущий статус: {from_status}"
        )
    )
    db.add(process_log)
    
    # Запись в audit_log
    audit_log = AuditLog(
        user_login="system",
        action_type="COMMAND_RESET",
        message=(
            f"Выполнен Command_Reset для сессии #{process_run_id}. "
            f"Предыдущий статус: {from_status}"
        )
    )
    db.add(audit_log)
    
    # Запись в state_history
    await state_history_service.log_transition(
        db,
        process_run_id=process_run_id,
        entity_type="process_run",
        from_status=from_status,
        to_status="IDLE",
        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
        reason="Command_Reset: принудительный сброс сессии",
        triggered_by="system"
    )
    
    await db.flush()
    await db.refresh(process_run)
    
    return process_run