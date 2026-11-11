-- ====================================================================================================================================
-- СКРИПТ ТЕСТОВЫХ ДАННЫХ (SEED)
-- Проект: AutomaticScan
-- Версия: 1.1 (исправлены синтаксические ошибки)
-- ====================================================================================================================================


-- ====================================================================================================================================
-- ЧАСТЬ 1: ОЧИСТКА ТАБЛИЦ
-- ====================================================================================================================================


TRUNCATE TABLE audit_log RESTART IDENTITY CASCADE;
TRUNCATE TABLE process_log RESTART IDENTITY CASCADE;
TRUNCATE TABLE scan_result RESTART IDENTITY CASCADE;
TRUNCATE TABLE stage_run RESTART IDENTITY CASCADE;
TRUNCATE TABLE process_run RESTART IDENTITY CASCADE;
TRUNCATE TABLE host RESTART IDENTITY CASCADE;
TRUNCATE TABLE "group" RESTART IDENTITY CASCADE;


-- ====================================================================================================================================
-- ЧАСТЬ 2: ГРУППЫ (ДОПОЛНИТЕЛЬНЫЕ ОФИСЫ)
-- ====================================================================================================================================


INSERT INTO "group" (name, subnet, scan_schedule, is_active) VALUES
    ('Обнаружение пользовательских компьютеров СЭиИБ',         '10.77.110.0/24',   '0 2 * * 1',  FALSE),
    ('Обнаружение пользовательских компьютеров ДО Красные Ворота', '10.77.14.0/24',    '0 3 * * 2',  FALSE),
    ('Обнаружение пользовательских компьютеров ДО Санкт-Петербург', '192.168.110.0/24', '0 4 * * 3',  FALSE);


-- ====================================================================================================================================
-- ЧАСТЬ 3: ХОСТЫ (РАБОЧИЕ КОМПЬЮТЕРЫ)
-- ====================================================================================================================================


-- Хосты для группы 1: СЭиИБ

INSERT INTO host (group_id, ip_address, hostname) VALUES
    (1, '10.77.110.45', '0001_WIN10_RUS'),
    (1, '10.77.110.46', '0002_WIN10_RUS');

-- Хосты для группы 2: ДО Красные Ворота

INSERT INTO host (group_id, ip_address, hostname) VALUES
    (2, '10.77.14.60', '0003_WIN10_RUS'),
    (2, '10.77.14.61', '0004_WIN10_RUS');

-- Хосты для группы 3: ДО Санкт-Петербург

INSERT INTO host (group_id, ip_address, hostname) VALUES
    (3, '192.168.110.77', 'spb-pc-005'),
    (3, '192.168.110.78', 'spb-pc-006');


-- ====================================================================================================================================
-- ЧАСТЬ 4: СЕССИИ СКАНИРОВАНИЯ (process_run)
-- ====================================================================================================================================


-- Сессия 1: успешно завершена вчера

INSERT INTO process_run (started_at, ended_at, status, initiated_by) VALUES
    (NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '2 hours', 'SUCCESS', 'manual');

-- Сессия 2: в процессе выполнения (запущена 10 минут назад)

INSERT INTO process_run (started_at, ended_at, status, initiated_by) VALUES
    (NOW() - INTERVAL '10 minutes', NULL, 'IN_PROGRESS', 'scheduler');

-- Сессия 3: завершена с ошибкой 2 дня назад

INSERT INTO process_run (started_at, ended_at, status, initiated_by) VALUES
    (NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '30 minutes', 'FAILED', 'manual');


-- ====================================================================================================================================
-- ЧАСТЬ 5: ЭТАПЫ ВЫПОЛНЕНИЯ (stage_run)
-- ====================================================================================================================================


-- === Этапы для Сессии 1 (УСПЕШНАЯ) ===

INSERT INTO stage_run (process_run_id, current_stage, redcheck_job_id, is_stage_included, gate_decision, started_at, ended_at) VALUES
    (1, 'Stage_1_Actual',   '1', TRUE,  'ALLOW', NOW() - INTERVAL '1 day',                   NOW() - INTERVAL '1 day' + INTERVAL '10 minutes'),
    (1, 'Stage_2_Avail',    '2', TRUE,  'ALLOW', NOW() - INTERVAL '1 day' + INTERVAL '10 minutes',  NOW() - INTERVAL '1 day' + INTERVAL '20 minutes'),
    (1, 'Stage_3_Audit',    '3', TRUE,  'ALLOW', NOW() - INTERVAL '1 day' + INTERVAL '20 minutes',  NOW() - INTERVAL '1 day' + INTERVAL '90 minutes'),
    (1, 'Stage_4_Archiving', NULL,       TRUE,  'ALLOW', NOW() - INTERVAL '1 day' + INTERVAL '90 minutes',  NOW() - INTERVAL '1 day' + INTERVAL '100 minutes'),
    (1, 'Stage_5_Analytics', NULL,       TRUE,  'ALLOW', NOW() - INTERVAL '1 day' + INTERVAL '100 minutes', NOW() - INTERVAL '1 day' + INTERVAL '120 minutes');

-- === Этапы для Сессии 2 (В ПРОЦЕССЕ, С HOLD) ===

INSERT INTO stage_run (process_run_id, current_stage, redcheck_job_id, is_stage_included, gate_decision, started_at, ended_at) VALUES
    (2, 'Stage_1_Actual',   '4', TRUE,  'HOLD',  NOW() - INTERVAL '10 minutes', NULL),
    (2, 'Stage_2_Avail',    NULL,       TRUE,  NULL,    NULL, NULL),
    (2, 'Stage_3_Audit',    NULL,       FALSE, 'SKIP',   NULL, NULL),
    (2, 'Stage_4_Archiving', NULL,       TRUE,  NULL,    NULL, NULL),
    (2, 'Stage_5_Analytics', NULL,       TRUE,  NULL,    NULL, NULL);

-- === Этапы для Сессии 3 (С ОШИБКОЙ) ===

INSERT INTO stage_run (process_run_id, current_stage, redcheck_job_id, is_stage_included, gate_decision, started_at, ended_at) VALUES
    (3, 'Stage_1_Actual',   '5', TRUE,  'ALLOW', NOW() - INTERVAL '2 days',                   NOW() - INTERVAL '2 days' + INTERVAL '5 minutes'),
    (3, 'Stage_2_Avail',    '6', TRUE,  'ABORT', NOW() - INTERVAL '2 days' + INTERVAL '5 minutes',  NOW() - INTERVAL '2 days' + INTERVAL '15 minutes'),
    (3, 'Stage_3_Audit',    NULL,       TRUE,  NULL,    NULL, NULL),
    (3, 'Stage_4_Archiving', NULL,       TRUE,  NULL,    NULL, NULL),
    (3, 'Stage_5_Analytics', NULL,       TRUE,  NULL,    NULL, NULL);


-- ====================================================================================================================================
-- ЧАСТЬ 6: РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ (scan_result)
-- ====================================================================================================================================


-- Результаты для группы 1: СЭиИБ (хосты 1 и 2)

INSERT INTO scan_result (process_run_id, host_id, is_accessible, lowSeverity_count, mediumSeverity_count, highSeverity_count, criticalSeverity_count) VALUES
    (1, 1, TRUE,  2, 1, 0, 0),   -- 0001_WIN10_RUS: низкие и средние уязвимости
    (1, 2, TRUE,  5, 3, 2, 1);   -- 0002_WIN10_RUS: много уязвимостей

-- Результаты для группы 2: ДО Красные Ворота (хосты 3 и 4)

INSERT INTO scan_result (process_run_id, host_id, is_accessible, lowSeverity_count, mediumSeverity_count, highSeverity_count, criticalSeverity_count) VALUES
    (1, 3, TRUE,  1, 0, 0, 0),   -- 0003_WIN10_RUS
    (1, 4, FALSE, 0, 0, 0, 0);   -- 0004_WIN10_RUS: недоступен при сканировании

-- Результаты для группы 3: ДО Санкт-Петербург (хосты 5 и 6)

INSERT INTO scan_result (process_run_id, host_id, is_accessible, lowSeverity_count, mediumSeverity_count, highSeverity_count, criticalSeverity_count) VALUES
    (1, 5, TRUE,  0, 1, 0, 0),   -- spb-pc-005
    (1, 6, TRUE,  2, 0, 0, 0);   -- spb-pc-006


-- ====================================================================================================================================
-- ЧАСТЬ 7: ТЕХНИЧЕСКИЕ ЛОГИ (process_log)
-- ====================================================================================================================================


-- Логи для Сессии 2 (в процессе, этап Stage_1_Actual с HOLD — это stage_run_id = 6)

INSERT INTO process_log (stage_run_id, log_level, message, created_at) VALUES
    (6,  'INFO',    'Запуск этапа Stage_1_Actual для группы "Обнаружение пользовательских компьютеров СЭиИБ"',  NOW() - INTERVAL '10 minutes'),
    (6,  'INFO',    'Запрос к RedCheck API: получение перечня хостов',                                         NOW() - INTERVAL '9 minutes'),
    (6,  'INFO',    'Получено 2 хоста из логической группы',                                                    NOW() - INTERVAL '8 minutes'),
    (6,  'WARNING', 'Обнаружен 1 новый хост, отсутствующий в группе',                                          NOW() - INTERVAL '7 minutes'),
    (6,  'INFO',    'Обнаружен 1 хост, отсутствующий в новом перечне',                                         NOW() - INTERVAL '6 minutes'),
    (6,  'INFO',    'Переход в состояние HOLD: ожидание подтверждения удаления',                                NOW() - INTERVAL '5 minutes');

-- Логи для Сессии 3 (с ошибкой, этап Stage_2_Avail с ABORT — это stage_run_id = 11)

INSERT INTO process_log (stage_run_id, log_level, message, created_at) VALUES
    (11, 'INFO',    'Запуск этапа Stage_1_Actual для группы "Обнаружение пользовательских компьютеров ДО Санкт-Петербург"', NOW() - INTERVAL '2 days'),
    (11, 'INFO',    'Этап завершён успешно',                                         NOW() - INTERVAL '2 days' + INTERVAL '5 minutes'),
    (12, 'INFO',    'Запуск этапа Stage_2_Avail',                                    NOW() - INTERVAL '2 days' + INTERVAL '5 minutes'),
    (12, 'ERROR',   'RedCheck API вернул ошибку: connection timeout',                NOW() - INTERVAL '2 days' + INTERVAL '10 minutes'),
    (12, 'CRITICAL','Превышено время ожидания ответа от сканера',                    NOW() - INTERVAL '2 days' + INTERVAL '15 minutes'),
    (12, 'INFO',    'Переход в состояние ABORT, сессия завершена с ошибкой',         NOW() - INTERVAL '2 days' + INTERVAL '15 minutes');


-- ====================================================================================================================================
-- ЧАСТЬ 8: ЖУРНАЛ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ (audit_log)
-- ====================================================================================================================================


INSERT INTO audit_log (user_login, action_type, message, created_at) VALUES
    ('ivanov',     'LOGIN',           'Пользователь вошёл в систему',                       NOW() - INTERVAL '2 days'),
    ('ivanov',     'START_PROCESS',   'Запущен процесс сканирования вручную (Сессия №3)',   NOW() - INTERVAL '2 days'),
    ('ivanov',     'VIEW_SESSION',    'Просмотр деталей Сессии №1',                         NOW() - INTERVAL '1 day'),
    ('ivanov',     'EXPORT_REPORT',   'Экспорт аналитической отчётности в Excel',           NOW() - INTERVAL '1 day'),
    ('ivanov',     'LOGOUT',          'Пользователь вышел из системы',                      NOW() - INTERVAL '1 day'),
    ('petrov',     'LOGIN',           'Пользователь вошёл в систему',                       NOW() - INTERVAL '10 minutes'),
    ('petrov',     'START_PROCESS',   'Запущен процесс сканирования по расписанию',         NOW() - INTERVAL '10 minutes'),
    ('petrov',     'VIEW_DASHBOARD',  'Просмотр дашборда',                                  NOW() - INTERVAL '5 minutes');