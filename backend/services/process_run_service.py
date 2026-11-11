from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload  # Для eager loading связанных объектов
from typing import List
from ..models.process_run import ProcessRun
from ..models.stage_run import StageRun
from ..models.job import Job
from ..models.audit_log import AuditLog
from ..schemas.process_run import ProcessRunCreate, ProcessRunResponse
from ..services import state_history_service  # Для логирования переходов FSM


# ============================================================
# КОНСТАНТЫ
# ============================================================

# Единый набор статусов для ProcessRun и StageRun
VALID_STATUSES = [
    "IDLE",         # Ожидает запуска
    "IN_PROGRESS",  # Выполняется
    "SUCCESS",      # Завершён успешно
    "SKIPPED",      # Пропущен (только для StageRun)
    "HOLD",         # Приостановлен (ждёт подтверждения пользователя)
    "CANCELLED",    # Отменён пользователем
    "FAILED"        # Завершился с ошибкой
]

# Допустимые режимы запуска сессии
VALID_INITIATED_BY = ["manual", "scheduled"]

# Порядок этапов сканирования (всегда выполняется в этой последовательности)
STAGE_ORDER = [
    "Актуализация объектов",
    "Проверка доступности",
    "Аудит уязвимостей",
    "Размещение отчетов",
    "Формирование аналитики"
]

# Маппинг этапов на scan_type из RedCheck API
# Этапы 1-3 требуют задания в RedCheck, этапы 4-5 — нет
STAGE_TO_SCAN_TYPE = {
    "Актуализация объектов": 2,      # Инвентаризация
    "Проверка доступности": 20,      # Проверка доступности
    "Аудит уязвимостей": 5,          # Аудит уязвимостей
    "Размещение отчетов": None,      # Не требует задания
    "Формирование аналитики": None   # Не требует задания
}

# Типы действий для аудита
AUDIT_ACTION_CREATE = "CREATE_SESSION"
AUDIT_ACTION_START = "START_SESSION"
AUDIT_ACTION_HOLD = "HOLD_SESSION"
AUDIT_ACTION_CANCEL = "CANCEL_SESSION"
AUDIT_ACTION_RESET = "RESET_SESSION"
AUDIT_ACTION_DELETE = "DELETE_SESSION"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def find_redcheck_job_id(db: AsyncSession, group_id: int, scan_type: int) -> str | None:
    """Находит redcheck_id задания в RedCheck по группе и типу сканирования."""
    result = await db.execute(
        select(Job).where(
            Job.scan_type == scan_type,
            Job.is_deleted_in_redcheck == False
        )
    )
    jobs = result.scalars().all()
    
    for job in jobs:
        if job.groups_data:
            for group_info in job.groups_data:
                if group_info.get('id') == group_id:
                    return str(job.redcheck_id)
    
    return None


async def write_audit_log(db: AsyncSession, user_login: str, action_type: str, message: str) -> None:
    """Создаёт запись в журнале аудита."""
    audit_log = AuditLog(
        user_login=user_login,
        action_type=action_type,
        message=message
    )
    db.add(audit_log)


# ============================================================
# CRUD-ФУНКЦИИ
# ============================================================

async def create_process_run(
    db: AsyncSession,
    process_data: ProcessRunCreate,
    user_login: str = "anonymous"
) -> ProcessRun:
    """Создаёт новую сессию сканирования."""
    process_run = ProcessRun(
        group_id=process_data.group_id,
        status="IDLE",
        initiated_by=process_data.initiated_by
    )
    
    db.add(process_run)
    await db.flush()
    await db.refresh(process_run)
    
    # Аудит
    await write_audit_log(
        db, user_login, AUDIT_ACTION_CREATE,
        f"Создана сессия #{process_run.id} для группы {process_data.group_id}, "
        f"этапы: {', '.join(process_data.stages)}, режим: {process_data.initiated_by}"
    )
    
    # История FSM: NULL → IDLE (USER_ACTION)
    await state_history_service.log_transition(
        db,
        process_run_id=process_run.id,
        entity_type="process_run",
        from_status=None,
        to_status="IDLE",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Сессия создана",
        triggered_by=user_login
    )
    
    # Создаём этапы
    for stage_name in STAGE_ORDER:
        if stage_name not in process_data.stages:
            continue
        
        redcheck_job_id = None
        scan_type = STAGE_TO_SCAN_TYPE.get(stage_name)
        if scan_type:
            redcheck_job_id = await find_redcheck_job_id(db, process_data.group_id, scan_type)
        
        stage = StageRun(
            process_run_id=process_run.id,
            current_stage=stage_name,
            redcheck_job_id=redcheck_job_id,
            is_stage_included=True,
            status="IDLE"
        )
        db.add(stage)
    
    await db.flush()
    
    # После flush получаем ID этапов и записываем в историю
    result = await db.execute(
        select(StageRun).where(StageRun.process_run_id == process_run.id).order_by(StageRun.id.asc())
    )
    stages = result.scalars().all()
    
    for stage in stages:
        await state_history_service.log_transition(
            db,
            process_run_id=process_run.id,
            entity_type="stage_run",
            stage_run_id=stage.id,
            from_status=None,
            to_status="IDLE",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"Этап '{stage.current_stage}' создан",
            triggered_by="system"
        )
    
    await db.flush()
    return process_run


async def get_process_run(db: AsyncSession, process_run_id: int) -> ProcessRun:
    """Получает сессию по ID с этапами."""
    result = await db.execute(
        select(ProcessRun)
        .options(selectinload(ProcessRun.stages))
        .where(ProcessRun.id == process_run_id)
    )
    process_run = result.scalars().unique().first()
    
    if not process_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    
    return process_run


async def get_all_process_runs(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProcessRun]:
    """Получает список всех сессий с этапами."""
    result = await db.execute(
        select(ProcessRun)
        .options(selectinload(ProcessRun.stages))
        .order_by(ProcessRun.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().unique().all()


async def start_process_run(db: AsyncSession, process_run_id: int, user_login: str = "anonymous") -> ProcessRun:
    """Запускает или возобновляет сессию."""
    process_run = await get_process_run(db, process_run_id)
    from_status = process_run.status
    
    if process_run.status not in ["IDLE", "HOLD"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно запустить сессию со статусом {process_run.status}"
        )
    
    # Сессия: IDLE/HOLD → IN_PROGRESS (USER_ACTION)
    process_run.status = "IN_PROGRESS"
    process_run.started_at = datetime.utcnow()
    process_run.ended_at = None
    
    await write_audit_log(db, user_login, AUDIT_ACTION_START, f"Запущена сессия #{process_run.id}")
    
    await state_history_service.log_transition(
        db,
        process_run_id=process_run.id,
        entity_type="process_run",
        from_status=from_status,
        to_status="IN_PROGRESS",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Сессия запущена" if from_status == "IDLE" else "Сессия возобновлена после HOLD",
        triggered_by=user_login
    )
    
    # Логика для этапов
    if from_status == "HOLD":
        # Возобновление: этап HOLD → IN_PROGRESS (SYSTEM_AUTO)
        for stage in process_run.stages:
            if stage.status == "HOLD":
                stage_from_status = stage.status
                stage.status = "IN_PROGRESS"
                stage.started_at = datetime.utcnow()
                stage.ended_at = None
                
                await state_history_service.log_transition(
                    db,
                    process_run_id=process_run.id,
                    entity_type="stage_run",
                    stage_run_id=stage.id,
                    from_status=stage_from_status,
                    to_status="IN_PROGRESS",
                    transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                    reason=f"Этап '{stage.current_stage}' возобновлён после HOLD",
                    triggered_by="system"
                )
                break
    else:
        # Запуск из IDLE: первый этап IDLE → IN_PROGRESS (SYSTEM_AUTO)
        for stage in process_run.stages:
            if stage.is_stage_included and stage.status == "IDLE":
                stage_from_status = stage.status
                stage.status = "IN_PROGRESS"
                stage.started_at = datetime.utcnow()
                
                await state_history_service.log_transition(
                    db,
                    process_run_id=process_run.id,
                    entity_type="stage_run",
                    stage_run_id=stage.id,
                    from_status=stage_from_status,
                    to_status="IN_PROGRESS",
                    transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                    reason=f"Этап '{stage.current_stage}' запущен автоматически",
                    triggered_by="system"
                )
                break
    
    await db.flush()
    await db.refresh(process_run)
    return process_run


async def hold_process_run(db: AsyncSession, process_run_id: int, user_login: str = "anonymous") -> ProcessRun:
    """Приостанавливает сессию."""
    process_run = await get_process_run(db, process_run_id)
    from_status = process_run.status
    
    if process_run.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно приостановить сессию со статусом {process_run.status}"
        )
    
    # Сессия: IN_PROGRESS → HOLD (USER_ACTION)
    process_run.status = "HOLD"
    process_run.ended_at = datetime.utcnow()
    
    await write_audit_log(db, user_login, AUDIT_ACTION_HOLD, f"Приостановлена сессия #{process_run.id}")
    
    await state_history_service.log_transition(
        db,
        process_run_id=process_run.id,
        entity_type="process_run",
        from_status=from_status,
        to_status="HOLD",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Сессия приостановлена пользователем",
        triggered_by=user_login
    )
    
    # Текущий этап: IN_PROGRESS → HOLD (SYSTEM_AUTO)
    for stage in process_run.stages:
        if stage.status == "IN_PROGRESS":
            stage_from_status = stage.status
            stage.status = "HOLD"
            stage.ended_at = datetime.utcnow()
            
            await state_history_service.log_transition(
                db,
                process_run_id=process_run.id,
                entity_type="stage_run",
                stage_run_id=stage.id,
                from_status=stage_from_status,
                to_status="HOLD",
                transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                reason=f"Этап '{stage.current_stage}' приостановлен вместе с сессией",
                triggered_by="system"
            )
            break
    
    await db.flush()
    await db.refresh(process_run)
    return process_run


async def cancel_process_run(db: AsyncSession, process_run_id: int, user_login: str = "anonymous") -> ProcessRun:
    """
    Окончательно отменяет сессию и все её незавершённые этапы.
    
    Логика:
    1. Сессия переходит в CANCELLED (USER_ACTION)
    2. Все этапы в статусах IDLE/IN_PROGRESS/HOLD переходят в CANCELLED (SYSTEM_AUTO)
    3. Завершённые этапы (SUCCESS/SKIPPED/FAILED) НЕ трогаем
    4. Все переходы фиксируются в истории FSM
    """
    process_run = await get_process_run(db, process_run_id)
    from_status = process_run.status
    
    if process_run.status not in ["IDLE", "IN_PROGRESS", "HOLD"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно отменить сессию со статусом {process_run.status}"
        )
    
    # Сессия: → CANCELLED (USER_ACTION)
    process_run.status = "CANCELLED"
    process_run.ended_at = datetime.utcnow()
    
    await write_audit_log(db, user_login, AUDIT_ACTION_CANCEL, f"Отменена сессия #{process_run.id}")
    
    await state_history_service.log_transition(
        db,
        process_run_id=process_run.id,
        entity_type="process_run",
        from_status=from_status,
        to_status="CANCELLED",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Сессия отменена пользователем",
        triggered_by=user_login
    )
    
    # Отменяем все незавершённые этапы (SYSTEM_AUTO)
    # Завершённые этапы (SUCCESS/SKIPPED/FAILED) не трогаем
    for stage in process_run.stages:
        if stage.status in ["IDLE", "IN_PROGRESS", "HOLD"]:
            stage_from_status = stage.status
            stage.status = "CANCELLED"
            stage.ended_at = datetime.utcnow()
            
            await state_history_service.log_transition(
                db,
                process_run_id=process_run.id,
                entity_type="stage_run",
                stage_run_id=stage.id,
                from_status=stage_from_status,
                to_status="CANCELLED",
                transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                reason=f"Этап '{stage.current_stage}' отменён вместе с сессией",
                triggered_by="system"
            )
    
    await db.flush()
    await db.refresh(process_run)
    return process_run


async def reset_process_run(db: AsyncSession, process_run_id: int, user_login: str = "anonymous") -> ProcessRun:
    """Сбрасывает сессию к начальному состоянию."""
    process_run = await get_process_run(db, process_run_id)
    from_status = process_run.status
    
    # Сбрасываем все этапы
    result = await db.execute(select(StageRun).where(StageRun.process_run_id == process_run_id))
    stages = result.scalars().all()
    
    for stage in stages:
        stage_from_status = stage.status
        stage.status = "IDLE"
        stage.gate_decision = None
        stage.stage_output_status = None
        stage.started_at = None
        stage.ended_at = None
        
        # История для этапа
        await state_history_service.log_transition(
            db,
            process_run_id=process_run.id,
            entity_type="stage_run",
            stage_run_id=stage.id,
            from_status=stage_from_status,
            to_status="IDLE",
            transition_type=state_history_service.TRANSITION_USER_ACTION,
            reason=f"Этап '{stage.current_stage}' сброшен",
            triggered_by=user_login
        )
    
    # Сбрасываем сессию
    process_run.status = "IDLE"
    process_run.started_at = None
    process_run.ended_at = None
    process_run.error_message = None
    
    # Аудит
    await write_audit_log(db, user_login, AUDIT_ACTION_RESET, f"Сброшена сессия #{process_run.id}")
    
    # История для сессии
    await state_history_service.log_transition(
        db,
        process_run_id=process_run.id,
        entity_type="process_run",
        from_status=from_status,
        to_status="IDLE",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Сессия сброшена пользователем",
        triggered_by=user_login
    )
    
    await db.flush()
    await db.refresh(process_run)
    return process_run


async def delete_process_run(db: AsyncSession, process_run_id: int, user_login: str = "anonymous") -> None:
    """Удаляет сессию сканирования."""
    process_run = await get_process_run(db, process_run_id)
    from_status = process_run.status
    
    # Аудит ПЕРЕД удалением
    await write_audit_log(db, user_login, AUDIT_ACTION_DELETE, f"Удалена сессия #{process_run.id}")
    
    # История ПЕРЕД удалением
    await state_history_service.log_transition(
        db,
        process_run_id=process_run.id,
        entity_type="process_run",
        from_status=from_status,
        to_status="DELETED",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Сессия удалена пользователем",
        triggered_by=user_login
    )
    
    await db.delete(process_run)
    await db.flush()