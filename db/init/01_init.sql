-- ====================================================================================================================================
-- СКРИПТ ИНИЦИАЛИЗАЦИИ БАЗЫ ДАННЫХ
-- Проект: AutomaticScan
-- Версия: 1.0
-- ====================================================================================================================================


-- ====================================================================================================================================
-- ЧАСТЬ 1: РАСШИРЕНИЯ POSTGRESQL
-- ====================================================================================================================================


-- Расширения — это дополнительные модули PostgreSQL,
-- которые добавляют новые функции и типы данных.

-- uuid-ossp: генерация UUID (уникальных идентификаторов)
-- Пример UUID: 550e8400-e29b-41d4-a716-446655440000
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pg_trgm: поддержка нечёткого поиска по тексту
-- Полезно для поиска хостов по частичному совпадению имени
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- pgcrypto: криптографические функции
-- Понадобится для хеширования паролей и токенов
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ====================================================================================================================================
-- ЧАСТЬ 2: СОЗДАНИЕ ТАБЛИЦ ИЗ ERD
-- ====================================================================================================================================


-- ТАБЛИЦА 1: group (логические группы хостов)
-- Каждая группа = дополнительный офис банка

CREATE TABLE "group" (
    id SERIAL PRIMARY KEY,                    		-- Уникальный ID группы (автоинкремент)
    name VARCHAR(255) NOT NULL,               		-- Название группы (например, "Дополнительный офис №1")
    subnet VARCHAR(50),                       		-- Подсеть (например, "192.168.1.0/24")
    scan_schedule VARCHAR(50),                		-- Расписание сканирования (например, "0 2 * * 1" = каждый понедельник в 2:00)
    is_active BOOLEAN NOT NULL DEFAULT FALSE            -- Флаг активности группы (TRUE = группа активна)
);



-- ТАБЛИЦА 2: process_run (сессии сканирования)
-- Каждая запись = один запуск полного процесса (ручной или по расписанию)

CREATE TABLE process_run (
    id SERIAL PRIMARY KEY,                    		-- Уникальный ID сессии
    started_at TIMESTAMP DEFAULT NOW(),       		-- Время запуска сессии (по умолчанию = текущее время)
    ended_at TIMESTAMP,                       		-- Время завершения сессии (NULL если ещё не завершена)
    status VARCHAR(30) NOT NULL DEFAULT 'IDLE', 	-- Статус сессии: IDLE, IN_PROGRESS, SUCCESS, FAILED
    initiated_by VARCHAR(50)                  		-- Кто запустил: "manual" (вручную) или "scheduler" (по расписанию)
);



-- ТАБЛИЦА 3: host (хосты/объекты инфраструктуры)
-- Каждый хост = рабочий компьютер сотрудника

CREATE TABLE host (
    id SERIAL PRIMARY KEY,                    		-- Уникальный ID хоста
    group_id INTEGER NOT NULL,                		-- ID группы, к которой принадлежит хост (связь с таблицей group)
    ip_address VARCHAR(45) NOT NULL,          		-- IP-адрес хоста (например, "192.168.1.100")
    hostname VARCHAR(100),                    		-- Имя хоста в сети (например, "WORKSTATION-001")
    
    -- Внешний ключ: хост принадлежит группе
    -- ON DELETE CASCADE = если удалить группу, удалятся все её хосты
    FOREIGN KEY (group_id) REFERENCES "group"(id) ON DELETE CASCADE
);



-- ТАБЛИЦА 4: stage_run (этапы выполнения)
-- Каждый процесс состоит из 5 этапов (Stage_1 ... Stage_5)

CREATE TABLE stage_run (
    id SERIAL PRIMARY KEY,                    		-- Уникальный ID этапа
    process_run_id INTEGER NOT NULL,          		-- ID сессии, к которой принадлежит этап (связь с process_run)
    current_stage VARCHAR(100) NOT NULL,      		-- Название этапа (например, "Stage_1_Actual")
    redcheck_job_id VARCHAR(100),             		-- ID задания в RedCheck (для отслеживания)
    is_stage_included BOOLEAN NOT NULL,   		-- Включён ли этап в план (TRUE = выполнять, FALSE = пропустить)
    gate_decision VARCHAR(20),                		-- Решение DMN: ALLOW, SKIP, HOLD, ABORT
    started_at TIMESTAMP,                     		-- Время начала этапа
    ended_at TIMESTAMP,                       		-- Время завершения этапа
    
    -- Внешний ключ: этап принадлежит сессии
    FOREIGN KEY (process_run_id) REFERENCES process_run(id) ON DELETE CASCADE
);



-- ТАБЛИЦА 5: scan_result (результаты сканирования)
-- Хранит агрегированные данные по уязвимостям для каждого хоста

CREATE TABLE scan_result (
    id SERIAL PRIMARY KEY,                    		-- Уникальный ID результата
    process_run_id INTEGER NOT NULL,          		-- ID сессии сканирования (связь с process_run)
    host_id INTEGER NOT NULL,                 		-- ID хоста (связь с host)
    is_accessible BOOLEAN NOT NULL,       		-- Доступен ли хост при сканировании
    lowSeverity_count INTEGER DEFAULT 0,      		-- Количество уязвимостей низкого уровня (CVSS 0.1-3.9)
    mediumSeverity_count INTEGER DEFAULT 0,   		-- Количество уязвимостей среднего уровня (CVSS 4.0-6.9)
    highSeverity_count INTEGER DEFAULT 0,     		-- Количество уязвимостей высокого уровня (CVSS 7.0-8.9)
    criticalSeverity_count INTEGER DEFAULT 0, 		-- Количество уязвимостей критического уровня (CVSS 9.0-10.0)
    
    -- Внешние ключи
    FOREIGN KEY (process_run_id) REFERENCES process_run(id) ON DELETE CASCADE,
    FOREIGN KEY (host_id) REFERENCES host(id) ON DELETE CASCADE
);



-- ТАБЛИЦА 6: process_log (технические логи)
-- Хранит системные сообщения о выполнении этапов

CREATE TABLE process_log (
    id BIGSERIAL PRIMARY KEY,                 -- Уникальный ID лога (BIGSERIAL для большого количества записей)
    stage_run_id INTEGER NOT NULL,            -- ID этапа, к которому относится лог (связь с stage_run)
    log_level VARCHAR(20) NOT NULL,           -- Уровень лога: INFO, WARNING, ERROR, CRITICAL
    message TEXT NOT NULL,                    -- Текст сообщения
    created_at TIMESTAMP DEFAULT NOW(),       -- Время создания записи
    
    -- Внешний ключ: лог принадлежит этапу
    FOREIGN KEY (stage_run_id) REFERENCES stage_run(id) ON DELETE CASCADE
);



-- ТАБЛИЦА 7: audit_log (журнал действий пользователя)
-- Хранит действия специалиста в веб-интерфейсе

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,                 -- Уникальный ID записи
    user_login VARCHAR(50) NOT NULL,          -- Логин пользователя (например, "ivanov")
    action_type VARCHAR(50) NOT NULL,         -- Тип действия (например, "START_PROCESS", "CONFIRM_DELETE")
    message TEXT,                             -- Описание действия
    created_at TIMESTAMP DEFAULT NOW()        -- Время действия
);


-- ====================================================================================================================================
-- ЧАСТЬ 4: ИНДЕКСЫ ДЛЯ УСКОРЕНИЯ ПОИСКА
-- ====================================================================================================================================


-- Индексы работают как оглавление в книге:
-- без них PostgreSQL вынужден просматривать всю таблицу,
-- с индексами он сразу находит нужные строки.

-- Индексы для таблицы host
CREATE INDEX idx_host_group_id ON host(group_id);           			-- Ускоряет поиск хостов по группе
CREATE INDEX idx_host_ip_address ON host(ip_address);       			-- Ускоряет поиск хоста по IP

-- Индексы для таблицы scan_result
CREATE INDEX idx_scan_result_process_run_id ON scan_result(process_run_id);  	-- Поиск результатов по сессии
CREATE INDEX idx_scan_result_host_id ON scan_result(host_id);                	-- Поиск результатов по хосту

-- Индексы для таблицы stage_run
CREATE INDEX idx_stage_run_process_run_id ON stage_run(process_run_id);      	-- Поиск этапов по сессии
CREATE INDEX idx_stage_run_current_stage ON stage_run(current_stage);        	-- Поиск этапов по названию

-- Индексы для таблицы process_log
CREATE INDEX idx_process_log_stage_run_id ON process_log(stage_run_id);     	-- Поиск логов по этапу
CREATE INDEX idx_process_log_created_at ON process_log(created_at DESC);     	-- Поиск логов по времени (новые сверху)

-- Индексы для таблицы audit_log
CREATE INDEX idx_audit_log_user_login ON audit_log(user_login);              	-- Поиск действий по пользователю
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);         	-- Поиск действий по времени