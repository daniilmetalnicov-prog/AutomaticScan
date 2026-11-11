from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..models.state_history import StateHistory


# Типы переходов
TRANSITION_USER_ACTION = "USER_ACTION"
TRANSITION_SYSTEM_AUTO = "SYSTEM_AUTO"
TRANSITION_DMN_DECISION = "DMN_DECISION"
TRANSITION_ERROR = "ERROR"


async def log_transition(
    db: AsyncSession,
    process_run_id: int,
    entity_type: str,
    to_status: str,
    triggered_by: str,
    stage_run_id: Optional[int] = None,
    from_status: Optional[str] = None,
    transition_type: str = TRANSITION_USER_ACTION,
    reason: Optional[str] = None
) -> StateHistory:
    """
    Записывает переход состояния в историю.
    
    Args:
        db: Сессия базы данных
        process_run_id: ID сессии
        entity_type: Тип сущности ("process_run" или "stage_run")
        to_status: Новый статус
        triggered_by: Кто инициировал (логин или "system")
        stage_run_id: ID этапа (если переход на уровне этапа)
        from_status: Предыдущий статус (если известен)
        transition_type: Тип перехода (USER_ACTION, SYSTEM_AUTO, и т.д.)
        reason: Причина перехода
    
    Returns:
        Созданная запись StateHistory
    """
    history = StateHistory(
        process_run_id=process_run_id,
        entity_type=entity_type,
        stage_run_id=stage_run_id,
        from_status=from_status,
        to_status=to_status,
        transition_type=transition_type,
        reason=reason,
        triggered_by=triggered_by,
        transition_at=datetime.utcnow()
    )
    
    db.add(history)
    await db.flush()
    await db.refresh(history)
    
    return history


async def get_history_by_process_run(
    db: AsyncSession,
    process_run_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[StateHistory]:
    """Получает историю переходов для конкретной сессии."""
    result = await db.execute(
        select(StateHistory)
        .where(StateHistory.process_run_id == process_run_id)
        .order_by(StateHistory.transition_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_history_by_stage_run(
    db: AsyncSession,
    stage_run_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[StateHistory]:
    """Получает историю переходов для конкретного этапа."""
    result = await db.execute(
        select(StateHistory)
        .where(StateHistory.stage_run_id == stage_run_id)
        .order_by(StateHistory.transition_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_all_history(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[StateHistory]:
    """Получает всю историю переходов."""
    result = await db.execute(
        select(StateHistory)
        .order_by(StateHistory.transition_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()