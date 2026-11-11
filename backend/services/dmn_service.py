from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from ..models.dmn_rule import DmnRule
from ..models.stage_run import StageRun
from ..models.process_run import ProcessRun
from ..models.process_log import ProcessLog
from ..schemas.dmn_rule import DmnDecisionResponse


# ============================================================
# КОНСТАНТЫ
# ============================================================

# Маппинг уровней логирования DMN → process_log
# 
# Таблица dmn_rules использует свои значения уровней логирования:
#   - Log_Information
#   - Log_Warning
#   - Log_Critical
# 
# Таблица process_log имеет CHECK constraint, который разрешает только:
#   - INFO
#   - WARNING
#   - ERROR
#   - CRITICAL
# 
# Этот словарь преобразует значения DMN в допустимые для process_log.
# Возвращаемое значение DMN (в DmnDecisionResponse) остаётся оригинальным,
# чтобы клиент видел реальное решение из матрицы DMN.
DMN_TO_PROCESS_LOG_LEVEL = {
    "Log_Information": "INFO",
    "Log_Warning": "WARNING",
    "Log_Critical": "CRITICAL"
}


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ: ВЫЗОВ ДВИЖКА DMN
# ============================================================

async def evaluate_dmn(
    db: AsyncSession,
    stage_run_id: int
) -> DmnDecisionResponse:
    """
    Вызывает движок DMN для определения следующего шага выполнения сессии.
    
    Логика работы:
    1. Получает данные этапа из таблицы stage_run:
       - current_stage (название этапа)
       - is_stage_included (включён ли этап)
       - stage_output_status (результат выполнения этапа)
    
    2. Ищет подходящее правило в таблице dmn_rules с приоритетами:
       - Приоритет 1: точное совпадение по всем трём полям
         (current_stage + is_stage_included + stage_output_status)
       - Приоритет 2: правило для исключённого этапа
         (current_stage + is_stage_included=false + stage_output_status=NULL)
    
    3. Записывает решение в process_log (с маппингом log_level)
    
    4. Возвращает решение в формате DmnDecisionResponse
    
    Args:
        db: Сессия базы данных
        stage_run_id: ID этапа, для которого нужно принять решение
    
    Returns:
        DmnDecisionResponse — решение DMN, содержащее:
        - rule_id: ID применённого правила
        - current_stage: название текущего этапа
        - stage_output_status: результат выполнения этапа
        - target_next_stage: целевой следующий этап
        - gate_decision: решение шлюза (ALLOW/SKIP/HOLD/ABORT)
        - log_level: уровень логирования (оригинальное значение DMN)
        - email_alert: тип email-уведомления (если требуется)
        - annotations: аннотация к правилу
    
    Raises:
        HTTPException 404: Если этап с указанным ID не найден
        HTTPException 404: Если подходящее правило DMN не найдено
            (неожиданная комбинация current_stage + stage_output_status)
    
    Пример:
        Для этапа "Актуализация объектов" с stage_output_status="SUCCESS"
        будет найдено правило #2:
        - gate_decision: ALLOW
        - target_next_stage: "Проверка доступности"
        - log_level: "Log_Information"
    """
    # -------------------------------------------------------
    # Шаг 1: Получаем данные этапа
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
    # Шаг 2: Ищем подходящее правило в DMN
    # -------------------------------------------------------
    
    # Приоритет 1: точное совпадение по всем трём полям
    # Это основной сценарий — этап включён и имеет конкретный результат
    rule_result = await db.execute(
        select(DmnRule).where(
            DmnRule.current_stage == stage_run.current_stage,
            DmnRule.is_stage_included == stage_run.is_stage_included,
            DmnRule.stage_output_status == stage_run.stage_output_status
        )
    )
    rule = rule_result.scalars().first()
    
    # Приоритет 2: если точное совпадение не найдено — ищем правило
    # для исключённого этапа (is_stage_included=false, stage_output_status=NULL)
    # Этот сценарий актуален, если в будущем добавим механизм исключения
    # этапов после создания сессии
    if not rule:
        rule_result = await db.execute(
            select(DmnRule).where(
                DmnRule.current_stage == stage_run.current_stage,
                DmnRule.is_stage_included == False,
                DmnRule.stage_output_status.is_(None)
            )
        )
        rule = rule_result.scalars().first()
    
    # Если правило не найдено — это ошибка конфигурации DMN
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Правило DMN не найдено для этапа '{stage_run.current_stage}' "
                f"с is_stage_included={stage_run.is_stage_included} "
                f"и stage_output_status='{stage_run.stage_output_status}'. "
                f"Проверьте таблицу dmn_rules."
            )
        )
    
    # -------------------------------------------------------
    # Шаг 3: Получаем ID сессии для привязки лога
    # -------------------------------------------------------
    process_run_result = await db.execute(
        select(ProcessRun).where(ProcessRun.id == stage_run.process_run_id)
    )
    process_run = process_run_result.scalars().first()
    
    # -------------------------------------------------------
    # Шаг 4: Маппинг log_level и запись в process_log
    # -------------------------------------------------------
    
    # Преобразуем значение DMN (Log_Information) в значение process_log (INFO)
    # Это необходимо, т.к. в таблице process_log есть CHECK constraint,
    # который разрешает только INFO/WARNING/ERROR/CRITICAL
    process_log_level = DMN_TO_PROCESS_LOG_LEVEL.get(rule.log_level, "INFO")
    
    # Создаём запись в process_log с привязкой к сессии и этапу
    process_log = ProcessLog(
        process_run_id=process_run.id if process_run else None,
        stage_run_id=stage_run.id,
        log_level=process_log_level,
        message=(
            f"DMN Decision: {rule.gate_decision} → {rule.target_next_stage}. "
            f"{rule.annotations}"
        )
    )
    db.add(process_log)
    
    # -------------------------------------------------------
    # Шаг 5: Возвращаем решение DMN
    # -------------------------------------------------------
    
    # Важно: в ответе возвращаем ОРИГИНАЛЬНОЕ значение log_level из DMN
    # (Log_Information), а не замапленное (INFO).
    # Это нужно, чтобы клиент видел реальное решение из матрицы DMN
    # и мог корректно его интерпретировать.
    return DmnDecisionResponse(
        rule_id=rule.id,
        current_stage=rule.current_stage,
        stage_output_status=stage_run.stage_output_status,
        target_next_stage=rule.target_next_stage,
        gate_decision=rule.gate_decision,
        log_level=rule.log_level,  # Оригинальное значение DMN
        email_alert=rule.email_alert,
        annotations=rule.annotations
    )