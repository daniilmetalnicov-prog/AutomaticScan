from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.stage_run import StageRun
from ..services import (
    stage_1_actualization_service,
    stage_2_availability_service,
    stage_3_audit_service,
    stage_4_reports_service,
    stage_5_analytics_service,
    stage_run_service  # Для вызова complete_stage_with_dmn
)


# ============================================================
# REGISTRY-ПАТТЕРН: Маппинг названий этапов на обработчики
# ============================================================

STAGE_HANDLERS = {
    "Актуализация объектов": stage_1_actualization_service.execute,
    "Проверка доступности": stage_2_availability_service.execute,
    "Аудит уязвимостей": stage_3_audit_service.execute,
    "Размещение отчетов": stage_4_reports_service.execute,
    "Формирование аналитики": stage_5_analytics_service.execute
}


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ ОРКЕСТРАТОРА
# ============================================================

async def execute_stage(db: AsyncSession, stage_run_id: int) -> StageRun:
    """
    Оркестратор выполнения этапа.
    
    Логика:
    1. Получает этап по ID
    2. Проверяет, что этап в статусе IN_PROGRESS
    3. Находит обработчик в registry по названию этапа
    4. Делегирует выполнение специализированному сервису
    5. Сервис возвращает stage_output_status (строку)
    6. Вызывает complete_stage_with_dmn для применения решения DMN
    
    Args:
        db: Сессия базы данных
        stage_run_id: ID этапа
    
    Returns:
        Обновлённый объект StageRun (после применения DMN)
    
    Raises:
        HTTPException 404: Если этап не найден
        HTTPException 400: Если этап не в статусе IN_PROGRESS
        HTTPException 400: Если для этапа нет обработчика в registry
    """
    # -------------------------------------------------------
    # Шаг 1: Получаем этап по ID
    # -------------------------------------------------------
    result = await db.execute(
        select(StageRun).where(StageRun.id == stage_run_id)
    )
    stage_run = result.scalars().first()
    
    if not stage_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Этап не найден"
        )
    
    # -------------------------------------------------------
    # Шаг 2: Проверяем статус этапа
    # -------------------------------------------------------
    if stage_run.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Невозможно выполнить этап со статусом {stage_run.status}. "
                f"Требуется статус IN_PROGRESS"
            )
        )
    
    # -------------------------------------------------------
    # Шаг 3: Находим обработчик в registry
    # -------------------------------------------------------
    handler = STAGE_HANDLERS.get(stage_run.current_stage)
    
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Нет обработчика для этапа '{stage_run.current_stage}'"
        )
    
    # -------------------------------------------------------
    # Шаг 4: Делегируем выполнение специализированному сервису
    # -------------------------------------------------------
    # Сервис выполняет реальную работу и возвращает stage_output_status
    stage_output_status = await handler(db, stage_run)
    
    # -------------------------------------------------------
    # Шаг 5: Вызываем complete_stage_with_dmn
    # -------------------------------------------------------
    # Эта функция:
    # 1. Устанавливает stage_output_status
    # 2. Вызывает DMN для получения решения
    # 3. Применяет решение (ALLOW/SKIP/HOLD/ABORT)
    return await stage_run_service.complete_stage_with_dmn(
        db, stage_run_id, stage_output_status, triggered_by="system"
    )