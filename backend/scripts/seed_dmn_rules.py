"""
Скрипт для заполнения таблицы dmn_rules 20 правилами из матрицы DMN.

Запуск:
    cd C:\Projects\AutomaticScan
    python -m backend.scripts.seed_dmn_rules
"""
import asyncio
import sys
import os

# Добавляем корень проекта в путь, чтобы импорты работали корректно
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text
from backend.core.database import engine  # ← исправленный импорт


# 20 правил из матрицы DMN
DMN_RULES = [
    # (current_stage, is_stage_included, stage_output_status, target_next_stage, gate_decision, log_level, email_alert, annotations)
    
    # Правила для этапа "Актуализация объектов"
    ("Актуализация объектов", False, None, "Проверка доступности", "SKIP", "Log_Information", None, 
     "Этап исключён специалистом из плана. Переход к следующему шагу в обход этапа."),
    ("Актуализация объектов", True, "SUCCESS", "Проверка доступности", "ALLOW", "Log_Information", None,
     "Объекты успешно актуализированы. Автоматический переход к следующему этапу."),
    ("Актуализация объектов", True, "PARTIAL_SUCCESS", "Проверка доступности", "HOLD", "Log_Information", "Approve_Email",
     "Состав объектов изменен. Ожидание ручного подтверждения специалиста. Направлен запрос на Approve_Email."),
    ("Актуализация объектов", True, "FAILED", "Проверка доступности", "ABORT", "Log_Critical", "Critical_Email",
     "Критический сбой актуализации объектов. Аварийная остановка процесса. Отправлено уведомление на Critical_Email."),
    
    # Правила для этапа "Проверка доступности"
    ("Проверка доступности", False, None, "Аудит уязвимостей", "SKIP", "Log_Information", None,
     "Этап исключён специалистом из плана. Переход к следующему шагу в обход этапа."),
    ("Проверка доступности", True, "ALL_ACCESSIBLE", "Аудит уязвимостей", "ALLOW", "Log_Information", None,
     "Все целевые объекты доступны. Автоматический переход к следующему этапу."),
    ("Проверка доступности", True, "PARTIAL_ACCESSIBLE", "Аудит уязвимостей", "ALLOW", "Log_Warning", None,
     "Целевые объекты доступны частично. Переход к следующему этапу разрешен. Сформирован лог Log_Warning."),
    ("Проверка доступности", True, "ZERO_ACCESSIBLE", "Аудит уязвимостей", "ABORT", "Log_Critical", "Critical_Email",
     "Все целевые объекты недоступны. Аварийная остановка процесса. Отправлено уведомление на Critical_Email."),
    ("Проверка доступности", True, "FAILED", "Аудит уязвимостей", "ABORT", "Log_Critical", "Critical_Email",
     "Критический сбой проверки доступности объектов. Аварийная остановка процесса. Отправлено уведомление на Critical_Email."),
    
    # Правила для этапа "Аудит уязвимостей"
    ("Аудит уязвимостей", False, None, "Process_End", "SKIP", "Log_Information", None,
     "Этап исключён специалистом из плана. Переход к параллельному шлюзу в обход этапа."),
    ("Аудит уязвимостей", True, "ALL_SCANNED", "Размещение отчетов", "ALLOW", "Log_Information", None,
     "Все объекты успешно прошли аудит. Допуск к параллельному этапу размещения отчетов разрешен."),
    ("Аудит уязвимостей", True, "ALL_SCANNED", "Формирование аналитики", "ALLOW", "Log_Information", None,
     "Все объекты успешно прошли аудит. Допуск к параллельному этапу формирования аналитики разрешен."),
    ("Аудит уязвимостей", True, "PARTIAL_SCANNED", "Process_End", "ABORT", "Log_Warning", "Warning_Email",
     "Аудит объектов завершен частично. Аварийная остановка процесса. Сформирован лог Log_Warning."),
    ("Аудит уязвимостей", True, "FAILED", "Process_End", "ABORT", "Log_Critical", "Critical_Email",
     "Критический сбой подсистемы аудита уязвимостей. Аварийная остановка процесса. Отправлено уведомление на Critical_Email."),
    
    # Правила для этапа "Размещение отчетов"
    ("Размещение отчетов", False, None, "Process_End", "SKIP", "Log_Information", None,
     "Этап исключён специалистом из плана. Направляем ветку по транзитному пути «Нет»."),
    ("Размещение отчетов", True, "REPORTS_PLACED", "Process_End", "ALLOW", "Log_Information", None,
     "Технические отчеты успешно размещены в сетевом каталоге. Ветка процесса успешно завершена."),
    ("Размещение отчетов", True, "FAILED", "Process_End", "ALLOW", "Log_Critical", "Critical_Email",
     "Критический сбой записи технических отчетов в сетевой каталог. Ветка остановлена, отправлено уведомление на Critical_Email."),
    
    # Правила для этапа "Формирование аналитики"
    ("Формирование аналитики", False, None, "Process_End", "SKIP", "Log_Information", None,
     "Этап исключён специалистом из плана. Направляем ветку по транзитному пути «Нет»."),
    ("Формирование аналитики", True, "ANALYTICS_GENERATED", "Process_End", "ALLOW", "Log_Information", None,
     "Аналитическая отчетность успешно сформирована. Ветка процесса успешно завершена."),
    ("Формирование аналитики", True, "FAILED", "Process_End", "ABORT", "Log_Critical", "Critical_Email",
     "Критический сбой формирования аналитической отчетности. Отправлено уведомление на Critical_Email."),
]


async def seed_dmn_rules():
    """Заполняет таблицу dmn_rules 20 правилами."""
    async with engine.begin() as conn:
        # Очищаем таблицу перед заполнением
        await conn.execute(text("TRUNCATE TABLE dmn_rules"))
        
        # Вставляем правила
        for rule in DMN_RULES:
            await conn.execute(
                text("""
                    INSERT INTO dmn_rules 
                    (current_stage, is_stage_included, stage_output_status, target_next_stage, gate_decision, log_level, email_alert, annotations)
                    VALUES (:current_stage, :is_stage_included, :stage_output_status, :target_next_stage, :gate_decision, :log_level, :email_alert, :annotations)
                """),
                {
                    "current_stage": rule[0],
                    "is_stage_included": rule[1],
                    "stage_output_status": rule[2],
                    "target_next_stage": rule[3],
                    "gate_decision": rule[4],
                    "log_level": rule[5],
                    "email_alert": rule[6],
                    "annotations": rule[7]
                }
            )
        
        print(f"Заполнено {len(DMN_RULES)} правил DMN")


if __name__ == "__main__":
    asyncio.run(seed_dmn_rules())