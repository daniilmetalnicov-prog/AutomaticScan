-- ====================================================================================================================================
-- СКРИПТ ОГРАНИЧЕНИЙ И ПРОВЕРОК
-- Проект: AutomaticScan
-- Версия: 1.0
-- ====================================================================================================================================


-- ====================================================================================================================================
-- ЧАСТЬ 1: CHECK-ОГРАНИЧЕНИЯ
-- ====================================================================================================================================


-- CHECK-ограничения проверяют, что значение поля
-- соответствует допустимому списку.

-- Ограничение для process_run.status
-- Статус сессии может быть только: IDLE, IN_PROGRESS, SUCCESS, FAILED
ALTER TABLE process_run
ADD CONSTRAINT chk_process_run_status 
CHECK (status IN ('IDLE', 'IN_PROGRESS', 'SUCCESS', 'FAILED'));

-- Ограничение для stage_run.gate_decision
-- Решение DMN может быть только: ALLOW, SKIP, HOLD, ABORT
ALTER TABLE stage_run
ADD CONSTRAINT chk_stage_run_gate_decision 
CHECK (gate_decision IN ('ALLOW', 'SKIP', 'HOLD', 'ABORT'));

-- Ограничение для process_log.log_level
-- Уровень лога может быть только: INFO, WARNING, ERROR, CRITICAL
ALTER TABLE process_log
ADD CONSTRAINT chk_process_log_log_level 
CHECK (log_level IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL'));


-- ====================================================================================================================================
-- ЧАСТЬ 2: UNIQUE-ОГРАНИЧЕНИЯ
-- ====================================================================================================================================


-- UNIQUE-ограничения гарантируют уникальность значений.

-- Уникальность IP в группе
-- Нельзя добавить два хоста с одинаковым IP в одну группу
ALTER TABLE host
ADD CONSTRAINT uq_host_group_ip 
UNIQUE (group_id, ip_address);


-- ====================================================================================================================================
-- ЧАСТЬ 3: ТРИГГЕРЫ
-- ====================================================================================================================================


-- Триггеры — это автоматические действия, которые выполняются
-- при изменении данных в таблице.

-- Функция для сброса is_active при завершении процесса
CREATE OR REPLACE FUNCTION reset_group_is_active()
RETURNS TRIGGER AS $$
BEGIN
    -- Если статус изменился на SUCCESS или FAILED
    IF NEW.status IN ('SUCCESS', 'FAILED') AND OLD.status != NEW.status THEN
        -- Находим группу, связанную с этой сессией
        -- (через stage_run -> host -> group)
        UPDATE "group"
        SET is_active = FALSE
        WHERE id IN (
            SELECT DISTINCT h.group_id
            FROM host h
            JOIN scan_result sr ON sr.host_id = h.id
            WHERE sr.process_run_id = NEW.id
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Создаём триггер на таблице process_run
-- Триггер срабатывает ПОСЛЕ обновления записи
CREATE TRIGGER trg_reset_group_is_active
AFTER UPDATE ON process_run
FOR EACH ROW
EXECUTE FUNCTION reset_group_is_active();