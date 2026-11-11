from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..models.stage_run import StageRun
from ..models.process_run import ProcessRun
from ..models.host import Host
from ..models.audit_log import AuditLog
from ..models.process_log import ProcessLog
from ..services import state_history_service
from ..services import dmn_service
from ..services import redcheck_client
from ..schemas.dmn_rule import DmnDecisionResponse


# ============================================================
# КОНСТАНТЫ
# ============================================================

VALID_STAGE_STATUSES = [
    "IDLE", "IN_PROGRESS", "SUCCESS", "SKIPPED", "HOLD", "CANCELLED", "FAILED"
]

VALID_GATE_DECISIONS = ["ALLOW", "SKIP", "HOLD", "ABORT"]

PROCESS_END = "Process_End"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def _get_process_run_for_stage(db: AsyncSession, stage_run: StageRun) -> ProcessRun:
    """Получает сессию для этапа."""
    result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == stage_run.process_run_id)
    )
    return result.scalars().first()


async def get_stage_run(db: AsyncSession, stage_run_id: int) -> StageRun:
    """Получает этап по ID."""
    result = await db.execute(
        select(StageRun).where(StageRun.id == stage_run_id)
    )
    stage_run = result.scalars().first()
    
    if not stage_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Этап не найден"
        )
    
    return stage_run


async def get_stages_by_process_run(
    db: AsyncSession,
    process_run_id: int
) -> List[StageRun]:
    """Получает все этапы сессии в порядке выполнения."""
    result = await db.execute(
        select(StageRun)
        .where(StageRun.process_run_id == process_run_id)
        .order_by(StageRun.id.asc())
    )
    return result.scalars().all()


async def _get_next_included_stage(
    db: AsyncSession,
    process_run_id: int,
    current_stage_id: int
) -> StageRun | None:
    """Получает следующий включённый этап после текущего."""
    result = await db.execute(
        select(StageRun)
        .where(
            StageRun.process_run_id == process_run_id,
            StageRun.id > current_stage_id,
            StageRun.is_stage_included == True
        )
        .order_by(StageRun.id.asc())
    )
    return result.scalars().first()


async def _find_next_stage_by_name(
    db: AsyncSession,
    process_run_id: int,
    target_stage_name: str
) -> StageRun | None:
    """Находит следующий включённый этап по имени."""
    result = await db.execute(
        select(StageRun)
        .where(
            StageRun.process_run_id == process_run_id,
            StageRun.current_stage == target_stage_name,
            StageRun.is_stage_included == True,
            StageRun.status == "IDLE"
        )
        .order_by(StageRun.id.asc())
    )
    return result.scalars().first()


async def _cancel_all_remaining_stages(
    db: AsyncSession,
    process_run_id: int,
    exclude_stage_id: int,
    triggered_by: str
) -> None:
    """Отменяет все незавершённые этапы сессии (кроме указанного)."""
    result = await db.execute(
        select(StageRun).where(StageRun.process_run_id == process_run_id)
    )
    stages = result.scalars().all()
    
    for stage in stages:
        if stage.id == exclude_stage_id:
            continue
        
        if stage.status in ["IDLE", "IN_PROGRESS", "HOLD"]:
            stage_from_status = stage.status
            stage.status = "CANCELLED"
            stage.ended_at = datetime.utcnow()
            
            await state_history_service.log_transition(
                db,
                process_run_id=process_run_id,
                entity_type="stage_run",
                stage_run_id=stage.id,
                from_status=stage_from_status,
                to_status="CANCELLED",
                transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                reason=f"Этап '{stage.current_stage}' отменён из-за ABORT на этапе #{exclude_stage_id}",
                triggered_by=triggered_by
            )


# ============================================================
# ПРИМЕНЕНИЕ РЕШЕНИЯ DMN
# ============================================================

async def apply_dmn_decision(
    db: AsyncSession,
    stage_run: StageRun,
    decision: DmnDecisionResponse,
    triggered_by: str = "system"
) -> StageRun:
    """Применяет решение DMN к этапу и сессии."""
    process_run_id = stage_run.process_run_id
    
    process_run_result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == process_run_id)
    )
    process_run = process_run_result.scalars().first()
    
    gate_decision = decision.gate_decision
    target_next_stage = decision.target_next_stage
    
    if gate_decision == "ALLOW":
        stage_run.status = "SUCCESS"
        stage_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run_id, entity_type="stage_run",
            stage_run_id=stage_run.id, from_status="IN_PROGRESS", to_status="SUCCESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"DMN ALLOW: этап '{stage_run.current_stage}' завершён успешно",
            triggered_by=triggered_by
        )
        
        if target_next_stage == PROCESS_END:
            process_run.status = "SUCCESS"
            process_run.ended_at = datetime.utcnow()
            
            await state_history_service.log_transition(
                db, process_run_id=process_run_id, entity_type="process_run",
                from_status="IN_PROGRESS", to_status="SUCCESS",
                transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                reason="DMN ALLOW: все этапы завершены, сессия успешно завершена",
                triggered_by=triggered_by
            )
        else:
            next_stage = await _find_next_stage_by_name(db, process_run_id, target_next_stage)
            if not next_stage:
                next_stage = await _get_next_included_stage(db, process_run_id, stage_run.id)
            
            if next_stage:
                next_stage.status = "IN_PROGRESS"
                next_stage.started_at = datetime.utcnow()
                
                await state_history_service.log_transition(
                    db, process_run_id=process_run_id, entity_type="stage_run",
                    stage_run_id=next_stage.id, from_status="IDLE", to_status="IN_PROGRESS",
                    transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                    reason=f"DMN ALLOW: этап '{next_stage.current_stage}' запущен автоматически",
                    triggered_by=triggered_by
                )
            else:
                process_run.status = "SUCCESS"
                process_run.ended_at = datetime.utcnow()
                
                await state_history_service.log_transition(
                    db, process_run_id=process_run_id, entity_type="process_run",
                    from_status="IN_PROGRESS", to_status="SUCCESS",
                    transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                    reason="DMN ALLOW: этапы закончились, сессия завершена",
                    triggered_by=triggered_by
                )
    
    elif gate_decision == "SKIP":
        stage_run.status = "SKIPPED"
        stage_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run_id, entity_type="stage_run",
            stage_run_id=stage_run.id, from_status="IN_PROGRESS", to_status="SKIPPED",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"DMN SKIP: этап '{stage_run.current_stage}' пропущен",
            triggered_by=triggered_by
        )
        
        if target_next_stage == PROCESS_END:
            process_run.status = "SUCCESS"
            process_run.ended_at = datetime.utcnow()
            
            await state_history_service.log_transition(
                db, process_run_id=process_run_id, entity_type="process_run",
                from_status="IN_PROGRESS", to_status="SUCCESS",
                transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                reason="DMN SKIP: процесс завершён",
                triggered_by=triggered_by
            )
        else:
            next_stage = await _find_next_stage_by_name(db, process_run_id, target_next_stage)
            if not next_stage:
                next_stage = await _get_next_included_stage(db, process_run_id, stage_run.id)
            
            if next_stage:
                next_stage.status = "IN_PROGRESS"
                next_stage.started_at = datetime.utcnow()
                
                await state_history_service.log_transition(
                    db, process_run_id=process_run_id, entity_type="stage_run",
                    stage_run_id=next_stage.id, from_status="IDLE", to_status="IN_PROGRESS",
                    transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                    reason=f"DMN SKIP: этап '{next_stage.current_stage}' запущен после пропуска",
                    triggered_by=triggered_by
                )
    
    elif gate_decision == "HOLD":
        stage_run.status = "HOLD"
        stage_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run_id, entity_type="stage_run",
            stage_run_id=stage_run.id, from_status="IN_PROGRESS", to_status="HOLD",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"DMN HOLD: этап '{stage_run.current_stage}' ожидает подтверждения пользователя",
            triggered_by=triggered_by
        )
        
        process_run.status = "HOLD"
        process_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run_id, entity_type="process_run",
            from_status="IN_PROGRESS", to_status="HOLD",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason="DMN HOLD: сессия приостановлена, ожидание подтверждения пользователя",
            triggered_by=triggered_by
        )
    
    elif gate_decision == "ABORT":
        stage_run.status = "FAILED"
        stage_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run_id, entity_type="stage_run",
            stage_run_id=stage_run.id, from_status="IN_PROGRESS", to_status="FAILED",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"DMN ABORT: этап '{stage_run.current_stage}' завершился с ошибкой",
            triggered_by=triggered_by
        )
        
        process_run.status = "FAILED"
        process_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run_id, entity_type="process_run",
            from_status="IN_PROGRESS", to_status="FAILED",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason="DMN ABORT: сессия завершена с ошибкой",
            triggered_by=triggered_by
        )
        
        await _cancel_all_remaining_stages(db, process_run_id, stage_run.id, triggered_by)
    
    await db.flush()
    await db.refresh(stage_run)
    
    return stage_run


# ============================================================
# ЕДИНАЯ ТОЧКА ВХОДА: ЗАВЕРШЕНИЕ ЭТАПА С DMN
# ============================================================

async def complete_stage_with_dmn(
    db: AsyncSession,
    stage_run_id: int,
    stage_output_status: str,
    triggered_by: str = "system"
) -> StageRun:
    """Единая точка входа для завершения этапа с автоматическим вызовом DMN."""
    stage_run = await get_stage_run(db, stage_run_id)
    
    if stage_run.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно завершить этап со статусом {stage_run.status}. Требуется статус IN_PROGRESS"
        )
    
    stage_run.stage_output_status = stage_output_status
    
    decision = await dmn_service.evaluate_dmn(db, stage_run_id)
    
    return await apply_dmn_decision(db, stage_run, decision, triggered_by)


# ============================================================
# ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ: APPROVE / REJECT (с поддержкой двухфазного HOLD)
# ============================================================

async def approve_stage(
    db: AsyncSession,
    stage_run_id: int,
    user_login: str = "anonymous"
) -> StageRun:
    """
    Подтвердить действие на этапе (только для этапа в статусе HOLD).
    
    Для этапа 1 (Актуализация объектов) — двухфазное подтверждение:
    - Фаза REDCHECK: удалить устаревшие хосты из RedCheck → перейти в фазу DB
    - Фаза DB: удалить устаревшие хосты из БД → SUCCESS
    
    Для других этапов:
    - Перевести этап в SUCCESS и запустить следующий этап
    """
    stage_run = await get_stage_run(db, stage_run_id)
    
    if stage_run.status != "HOLD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно подтвердить этап со статусом {stage_run.status}. Требуется статус HOLD"
        )
    
    from_status = stage_run.status
    hold_data = stage_run.hold_data or {}
    phase = hold_data.get("phase")
    
    # ============================================================
    # СПЕЦИАЛЬНАЯ ЛОГИКА ДЛЯ ЭТАПА 1 (Актуализация объектов)
    # ============================================================
    if stage_run.current_stage == "Актуализация объектов" and phase:
        
        # --- Фаза 1: Удаление из RedCheck ---
        if phase == "REDCHECK":
            hosts_to_delete = hold_data.get("hosts_to_delete", [])
            redcheck_ids = [h.get("redcheck_id") for h in hosts_to_delete if h.get("redcheck_id")]
            
            if redcheck_ids:
                token = await redcheck_client.authenticate("admin", "admin")
                result = await redcheck_client.delete_hosts_bulk(redcheck_ids, token)
                
                process_log = ProcessLog(
                    process_run_id=stage_run.process_run_id,
                    stage_run_id=stage_run.id,
                    log_level="INFO",
                    message=f"Удалено {result.get('deleted', 0)} устаревших хостов из RedCheck"
                )
                db.add(process_log)
            
            # Переходим к фазе DB (остаёмся в HOLD!)
            stage_run.hold_data = {
                "phase": "DB",
                "hosts_to_delete": hosts_to_delete
            }
            
            audit_log = AuditLog(
                user_login=user_login,
                action_type="APPROVE_STAGE",
                message=f"Пользователь подтвердил удаление хостов из RedCheck (этап '{stage_run.current_stage}', сессия #{stage_run.process_run_id})"
            )
            db.add(audit_log)
            
            await state_history_service.log_transition(
                db, process_run_id=stage_run.process_run_id,
                entity_type="stage_run", stage_run_id=stage_run.id,
                from_status=from_status, to_status="HOLD",
                transition_type=state_history_service.TRANSITION_USER_ACTION,
                reason="Подтверждено удаление из RedCheck, ожидание подтверждения для БД",
                triggered_by=user_login
            )
            
            await db.flush()
            await db.refresh(stage_run)
            return stage_run  # ← РАННИЙ ВОЗВРАТ! Не доходим до стандартной логики
        
        # --- Фаза 2: Удаление из БД ---
        elif phase == "DB":
            hosts_to_delete = hold_data.get("hosts_to_delete", [])
            
            process_run = await _get_process_run_for_stage(db, stage_run)
            
            for host_data in hosts_to_delete:
                ip = host_data.get("connection_address")
                if ip and process_run:
                    result = await db.execute(
                        select(Host).where(
                            Host.connection_address == ip,
                            Host.group_id == process_run.group_id
                        )
                    )
                    host = result.scalars().first()
                    if host:
                        await db.delete(host)
            
            process_log = ProcessLog(
                process_run_id=stage_run.process_run_id,
                stage_run_id=stage_run.id,
                log_level="INFO",
                message=f"Удалено {len(hosts_to_delete)} устаревших хостов из БД"
            )
            db.add(process_log)
            
            # Завершаем этап
            stage_run.hold_data = None
            stage_run.status = "SUCCESS"
            stage_run.ended_at = datetime.utcnow()
            stage_run.stage_output_status = "USER_APPROVED"
            
            audit_log = AuditLog(
                user_login=user_login,
                action_type="APPROVE_STAGE",
                message=f"Пользователь подтвердил удаление хостов из БД (этап '{stage_run.current_stage}', сессия #{stage_run.process_run_id})"
            )
            db.add(audit_log)
            
            await state_history_service.log_transition(
                db, process_run_id=stage_run.process_run_id,
                entity_type="stage_run", stage_run_id=stage_run.id,
                from_status=from_status, to_status="SUCCESS",
                transition_type=state_history_service.TRANSITION_USER_ACTION,
                reason="Подтверждено удаление из БД, этап завершён",
                triggered_by=user_login
            )
            
            # Запускаем следующий этап
            if process_run:
                next_stage = await _get_next_included_stage(db, process_run.id, stage_run.id)
                
                if next_stage:
                    next_stage.status = "IN_PROGRESS"
                    next_stage.started_at = datetime.utcnow()
                    
                    await state_history_service.log_transition(
                        db, process_run_id=process_run.id,
                        entity_type="stage_run", stage_run_id=next_stage.id,
                        from_status="IDLE", to_status="IN_PROGRESS",
                        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                        reason=f"Этап '{next_stage.current_stage}' запущен после подтверждения",
                        triggered_by="system"
                    )
                    
                    process_run.status = "IN_PROGRESS"
                    process_run.ended_at = None
                    
                    await state_history_service.log_transition(
                        db, process_run_id=process_run.id,
                        entity_type="process_run",
                        from_status="HOLD", to_status="IN_PROGRESS",
                        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                        reason="Сессия возобновлена после подтверждения этапа",
                        triggered_by="system"
                    )
                else:
                    process_run.status = "SUCCESS"
                    process_run.ended_at = datetime.utcnow()
                    
                    await state_history_service.log_transition(
                        db, process_run_id=process_run.id,
                        entity_type="process_run",
                        from_status="HOLD", to_status="SUCCESS",
                        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                        reason="Все этапы завершены после подтверждения",
                        triggered_by="system"
                    )
            
            await db.flush()
            await db.refresh(stage_run)
            return stage_run  # ← РАННИЙ ВОЗВРАТ!
    
    # ============================================================
    # СТАНДАРТНАЯ ЛОГИКА ДЛЯ ОСТАЛЬНЫХ ЭТАПОВ
    # ============================================================
    stage_run.status = "SUCCESS"
    stage_run.ended_at = datetime.utcnow()
    stage_run.stage_output_status = "USER_APPROVED"
    
    process_run = await _get_process_run_for_stage(db, stage_run)
    
    audit_log = AuditLog(
        user_login=user_login,
        action_type="APPROVE_STAGE",
        message=f"Пользователь подтвердил действие на этапе '{stage_run.current_stage}' сессии #{process_run.id}"
    )
    db.add(audit_log)
    
    await state_history_service.log_transition(
        db, process_run_id=process_run.id,
        entity_type="stage_run", stage_run_id=stage_run.id,
        from_status=from_status, to_status="SUCCESS",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Пользователь подтвердил действие",
        triggered_by=user_login
    )
    
    next_stage = await _get_next_included_stage(db, process_run.id, stage_run.id)
    
    if next_stage:
        next_stage.status = "IN_PROGRESS"
        next_stage.started_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run.id,
            entity_type="stage_run", stage_run_id=next_stage.id,
            from_status="IDLE", to_status="IN_PROGRESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"Этап '{next_stage.current_stage}' запущен после подтверждения",
            triggered_by="system"
        )
        
        process_run.status = "IN_PROGRESS"
        process_run.ended_at = None
        
        await state_history_service.log_transition(
            db, process_run_id=process_run.id,
            entity_type="process_run",
            from_status="HOLD", to_status="IN_PROGRESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason="Сессия возобновлена после подтверждения этапа",
            triggered_by="system"
        )
    else:
        process_run.status = "SUCCESS"
        process_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run.id,
            entity_type="process_run",
            from_status="HOLD", to_status="SUCCESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason="Все этапы завершены после подтверждения",
            triggered_by="system"
        )
    
    await db.flush()
    await db.refresh(stage_run)
    
    return stage_run


async def reject_stage(
    db: AsyncSession,
    stage_run_id: int,
    user_login: str = "anonymous"
) -> StageRun:
    """
    Отклонить действие на этапе (только для этапа в статусе HOLD).
    
    Для этапа 1 (Актуализация объектов) — двухфазное отклонение:
    - Фаза REDCHECK: пропустить удаление из RedCheck → перейти в фазу DB
    - Фаза DB: пропустить удаление из БД → SUCCESS
    
    Для других этапов:
    - Перевести этап в SUCCESS и запустить следующий этап
    """
    stage_run = await get_stage_run(db, stage_run_id)
    
    if stage_run.status != "HOLD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно отклонить этап со статусом {stage_run.status}. Требуется статус HOLD"
        )
    
    from_status = stage_run.status
    hold_data = stage_run.hold_data or {}
    phase = hold_data.get("phase")
    
    # ============================================================
    # СПЕЦИАЛЬНАЯ ЛОГИКА ДЛЯ ЭТАПА 1 (Актуализация объектов)
    # ============================================================
    if stage_run.current_stage == "Актуализация объектов" and phase:
        
        # --- Фаза 1: Пропускаем удаление из RedCheck ---
        if phase == "REDCHECK":
            stage_run.hold_data = {
                "phase": "DB",
                "hosts_to_delete": hold_data.get("hosts_to_delete", [])
            }
            
            audit_log = AuditLog(
                user_login=user_login,
                action_type="REJECT_STAGE",
                message=f"Пользователь отклонил удаление хостов из RedCheck (этап '{stage_run.current_stage}', сессия #{stage_run.process_run_id})"
            )
            db.add(audit_log)
            
            await state_history_service.log_transition(
                db, process_run_id=stage_run.process_run_id,
                entity_type="stage_run", stage_run_id=stage_run.id,
                from_status=from_status, to_status="HOLD",
                transition_type=state_history_service.TRANSITION_USER_ACTION,
                reason="Отклонено удаление из RedCheck, ожидание подтверждения для БД",
                triggered_by=user_login
            )
            
            await db.flush()
            await db.refresh(stage_run)
            return stage_run  # ← РАННИЙ ВОЗВРАТ!
        
        # --- Фаза 2: Пропускаем удаление из БД ---
        elif phase == "DB":
            stage_run.hold_data = None
            stage_run.status = "SUCCESS"
            stage_run.ended_at = datetime.utcnow()
            stage_run.stage_output_status = "USER_REJECTED"
            
            # ✅ ДОБАВЛЕНО: Запись в process_log об отклонении
            process_log = ProcessLog(
                process_run_id=stage_run.process_run_id,
                stage_run_id=stage_run.id,
                log_level="INFO",
                message="Пользователь отклонил удаление хостов из БД. Этап завершён успешно."
            )
            db.add(process_log)
            
            audit_log = AuditLog(
                user_login=user_login,
                action_type="REJECT_STAGE",
                message=f"Пользователь отклонил удаление хостов из БД (этап '{stage_run.current_stage}', сессия #{stage_run.process_run_id})"
            )
            db.add(audit_log)
            
            await state_history_service.log_transition(
                db, process_run_id=stage_run.process_run_id,
                entity_type="stage_run", stage_run_id=stage_run.id,
                from_status=from_status, to_status="SUCCESS",
                transition_type=state_history_service.TRANSITION_USER_ACTION,
                reason="Отклонено удаление из БД, этап завершён",
                triggered_by=user_login
            )
            
            process_run = await _get_process_run_for_stage(db, stage_run)
            
            if process_run:
                next_stage = await _get_next_included_stage(db, process_run.id, stage_run.id)
                
                if next_stage:
                    next_stage.status = "IN_PROGRESS"
                    next_stage.started_at = datetime.utcnow()
                    
                    await state_history_service.log_transition(
                        db, process_run_id=process_run.id,
                        entity_type="stage_run", stage_run_id=next_stage.id,
                        from_status="IDLE", to_status="IN_PROGRESS",
                        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                        reason=f"Этап '{next_stage.current_stage}' запущен после отклонения",
                        triggered_by="system"
                    )
                    
                    process_run.status = "IN_PROGRESS"
                    process_run.ended_at = None
                    
                    await state_history_service.log_transition(
                        db, process_run_id=process_run.id,
                        entity_type="process_run",
                        from_status="HOLD", to_status="IN_PROGRESS",
                        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                        reason="Сессия возобновлена после отклонения этапа",
                        triggered_by="system"
                    )
                else:
                    # ✅ ДОБАВЛЕНО: Явное логирование завершения сессии
                    process_run.status = "SUCCESS"
                    process_run.ended_at = datetime.utcnow()
                    
                    session_end_log = ProcessLog(
                        process_run_id=process_run.id,
                        stage_run_id=None,
                        log_level="INFO",
                        message="Сессия успешно завершена после отклонения удаления хостов из БД."
                    )
                    db.add(session_end_log)
                    
                    await state_history_service.log_transition(
                        db, process_run_id=process_run.id,
                        entity_type="process_run",
                        from_status="HOLD", to_status="SUCCESS",
                        transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
                        reason="Все этапы завершены после отклонения",
                        triggered_by="system"
                    )
            
            await db.flush()
            await db.refresh(stage_run)
            return stage_run  # ← РАННИЙ ВОЗВРАТ!
    
    # ============================================================
    # СТАНДАРТНАЯ ЛОГИКА ДЛЯ ОСТАЛЬНЫХ ЭТАПОВ
    # ============================================================
    stage_run.status = "SUCCESS"
    stage_run.ended_at = datetime.utcnow()
    stage_run.stage_output_status = "USER_REJECTED"
    
    process_run = await _get_process_run_for_stage(db, stage_run)
    
    audit_log = AuditLog(
        user_login=user_login,
        action_type="REJECT_STAGE",
        message=f"Пользователь отклонил действие на этапе '{stage_run.current_stage}' сессии #{process_run.id}"
    )
    db.add(audit_log)
    
    await state_history_service.log_transition(
        db, process_run_id=process_run.id,
        entity_type="stage_run", stage_run_id=stage_run.id,
        from_status=from_status, to_status="SUCCESS",
        transition_type=state_history_service.TRANSITION_USER_ACTION,
        reason="Пользователь отклонил действие",
        triggered_by=user_login
    )
    
    next_stage = await _get_next_included_stage(db, process_run.id, stage_run.id)
    
    if next_stage:
        next_stage.status = "IN_PROGRESS"
        next_stage.started_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run.id,
            entity_type="stage_run", stage_run_id=next_stage.id,
            from_status="IDLE", to_status="IN_PROGRESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason=f"Этап '{next_stage.current_stage}' запущен после отклонения",
            triggered_by="system"
        )
        
        process_run.status = "IN_PROGRESS"
        process_run.ended_at = None
        
        await state_history_service.log_transition(
            db, process_run_id=process_run.id,
            entity_type="process_run",
            from_status="HOLD", to_status="IN_PROGRESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason="Сессия возобновлена после отклонения этапа",
            triggered_by="system"
        )
    else:
        process_run.status = "SUCCESS"
        process_run.ended_at = datetime.utcnow()
        
        await state_history_service.log_transition(
            db, process_run_id=process_run.id,
            entity_type="process_run",
            from_status="HOLD", to_status="SUCCESS",
            transition_type=state_history_service.TRANSITION_SYSTEM_AUTO,
            reason="Все этапы завершены после отклонения",
            triggered_by="system"
        )
    
    await db.flush()
    await db.refresh(stage_run)
    
    return stage_run