-- ================================================================
-- ServiceDesk CRM — Инициализация базы данных MySQL 8.0
-- Версия: 2.0 | Дата: 27.03.2026
-- Выполняется автоматически при старте MySQL-контейнера Docker.
-- Схема соответствует docs/sa/DB_Migrations.md (21 миграция, 20 таблиц).
-- ================================================================

CREATE DATABASE IF NOT EXISTS servicedesk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE servicedesk;

SET NAMES utf8mb4;
SET time_zone = '+00:00';
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- ВОЛНА 1: СПРАВОЧНИКИ (нет FK наружу)
-- ============================================================

CREATE TABLE IF NOT EXISTS equipment_models (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(200) NOT NULL,
    manufacturer            VARCHAR(200),
    warranty_period_months  INT UNSIGNED NOT NULL DEFAULT 12,
    is_deleted              TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_model_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS clients (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(200) NOT NULL,
    contract_type           ENUM('premium','standard','none') NOT NULL DEFAULT 'none',
    contract_number         VARCHAR(100),
    contract_valid_until    DATE,
    address                 VARCHAR(500),
    is_deleted              TINYINT(1) NOT NULL DEFAULT 0,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_client_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS spare_parts (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    article     VARCHAR(100) NOT NULL,
    name        VARCHAR(200) NOT NULL,
    unit        VARCHAR(20) NOT NULL DEFAULT 'шт.',
    qty_main    INT NOT NULL DEFAULT 0,
    is_deleted  TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_part_article (article)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 2: ПОЛЬЗОВАТЕЛИ
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name        VARCHAR(200) NOT NULL,
    position         VARCHAR(100) NOT NULL,
    department       VARCHAR(100) NOT NULL,
    phone            VARCHAR(20) NOT NULL,
    email            VARCHAR(150) NOT NULL,
    hire_date        DATE,
    status           ENUM('active','on_leave','dismissed') NOT NULL DEFAULT 'active',
    roles            JSON NOT NULL COMMENT 'Array of role strings',
    is_active        TINYINT(1) NOT NULL DEFAULT 1,
    is_deleted       TINYINT(1) NOT NULL DEFAULT 0,
    password_hash    VARCHAR(255) NOT NULL,
    telegram_chat_id VARCHAR(50) COMMENT 'Telegram chat_id для уведомлений (ADR-003)',
    invited_at       DATETIME,
    last_login_at    DATETIME,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS client_contacts (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    client_id     BIGINT UNSIGNED NOT NULL,
    name          VARCHAR(200) NOT NULL,
    phone         VARCHAR(20),
    email         VARCHAR(150),
    password_hash VARCHAR(255) COMMENT 'NULL = нет доступа к клиентскому порталу',
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_contact_email (email),
    FOREIGN KEY (client_id) REFERENCES clients(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 3: ПЕРСОНАЛ
-- ============================================================

CREATE TABLE IF NOT EXISTS engineer_competencies (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    engineer_id             BIGINT UNSIGNED NOT NULL,
    equipment_model_id      BIGINT UNSIGNED NOT NULL,
    certificate_number      VARCHAR(100),
    certificate_valid_until DATE,
    last_training_date      DATE,
    is_deleted              TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_eng_model (engineer_id, equipment_model_id),
    FOREIGN KEY (engineer_id) REFERENCES users(id),
    FOREIGN KEY (equipment_model_id) REFERENCES equipment_models(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS absences (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED NOT NULL,
    type        ENUM('vacation','sick_leave','other') NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    notes       TEXT,
    created_by  BIGINT UNSIGNED NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED COMMENT 'NULL = системное действие (Celery)',
    action      VARCHAR(100) NOT NULL,
    entity      VARCHAR(100) NOT NULL,
    entity_id   BIGINT UNSIGNED NOT NULL,
    old_value   JSON,
    new_value   JSON,
    ip_address  VARCHAR(45),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_entity (entity, entity_id),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_created (created_at)
    -- Нет FK на users намеренно: лог сохраняется после удаления пользователя (ADR-007)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 4: ОБОРУДОВАНИЕ
-- ============================================================

CREATE TABLE IF NOT EXISTS equipment (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    model_id            BIGINT UNSIGNED NOT NULL,
    serial_number       VARCHAR(100) NOT NULL,
    manufacture_date    DATE,
    sale_date           DATE NOT NULL,
    client_id           BIGINT UNSIGNED NOT NULL,
    install_address     VARCHAR(500) NOT NULL,
    warranty_start      DATE NOT NULL,
    warranty_end        DATE NOT NULL,
    status              ENUM('active','in_repair','written_off','transferred') NOT NULL DEFAULT 'active',
    warranty_status     ENUM('on_warranty','expiring','expired') NOT NULL DEFAULT 'on_warranty'
                        COMMENT 'Пересчитывается Celery-задачей ежедневно в 03:00 (ADR-002)',
    commissioned_at     DATE COMMENT 'Для отчёта по возрасту парка (UC-1006)',
    configuration       JSON COMMENT 'Модули, прошивка, комплектация (BR-F-1003)',
    is_deleted          TINYINT(1) NOT NULL DEFAULT 0,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (warranty_end > warranty_start),
    UNIQUE KEY uq_serial_number (serial_number),
    FOREIGN KEY (model_id) REFERENCES equipment_models(id),
    FOREIGN KEY (client_id) REFERENCES clients(id),
    INDEX idx_equipment_client (client_id),
    INDEX idx_equipment_status (status),
    INDEX idx_equipment_warranty (warranty_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipment_documents (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_id BIGINT UNSIGNED NOT NULL,
    doc_type     ENUM('passport','warranty','manual','act','other') NOT NULL,
    file_name    VARCHAR(255) NOT NULL,
    file_data    LONGBLOB NOT NULL COMMENT 'Файл хранится как BLOB (ADR-001). Лимит 20 МБ валидируется в FileService.',
    file_size_kb INT UNSIGNED NOT NULL,
    mime_type    VARCHAR(100) NOT NULL,
    uploaded_by  BIGINT UNSIGNED NOT NULL,
    uploaded_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted   TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
    INDEX idx_equip_docs (equipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipment_history (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_id    BIGINT UNSIGNED NOT NULL,
    event_type      ENUM('initial_assignment','transfer','return','write_off') NOT NULL,
    from_client_id  BIGINT UNSIGNED,
    to_client_id    BIGINT UNSIGNED,
    return_type     ENUM('warranty_replacement','buyback'),
    return_date     DATE,
    reason          TEXT,
    claim_created   TINYINT(1) NOT NULL DEFAULT 0,
    recorded_by     BIGINT UNSIGNED NOT NULL,
    recorded_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (from_client_id) REFERENCES clients(id),
    FOREIGN KEY (to_client_id) REFERENCES clients(id),
    FOREIGN KEY (recorded_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS maintenance_schedules (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_id            BIGINT UNSIGNED NOT NULL,
    interval_months         INT UNSIGNED NOT NULL,
    first_maintenance_date  DATE NOT NULL,
    next_maintenance_date   DATE NOT NULL,
    last_ticket_created_at  DATE,
    is_active               TINYINT(1) NOT NULL DEFAULT 1,
    created_by              BIGINT UNSIGNED NOT NULL,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_maintenance_equipment (equipment_id),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS repair_history (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_id BIGINT UNSIGNED NOT NULL,
    ticket_id    BIGINT UNSIGNED COMMENT 'NULL при ручном вводе истории',
    work_type    ENUM('warranty_repair','planned_maintenance','unplanned_repair','installation') NOT NULL,
    work_date    DATE NOT NULL,
    engineer_id  BIGINT UNSIGNED,
    parts_used   JSON COMMENT '[{part_id, name, qty}] — денормализованный снапшот на момент записи',
    description  TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (engineer_id) REFERENCES users(id),
    INDEX idx_repair_equipment (equipment_id),
    INDEX idx_repair_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 5: ЗАЯВКИ
-- ============================================================

CREATE TABLE IF NOT EXISTS work_templates (
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(200) NOT NULL,
    equipment_model_id BIGINT UNSIGNED NOT NULL,
    work_items         JSON NOT NULL COMMENT '[{"seq":1,"description":"..."}] — минимум 1 элемент (UC-911)',
    parts              JSON COMMENT '[{"part_id":1,"qty":2}]',
    created_by         BIGINT UNSIGNED NOT NULL,
    is_deleted         TINYINT(1) NOT NULL DEFAULT 0,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_model_id) REFERENCES equipment_models(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tickets (
    id                       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_number            VARCHAR(20) NOT NULL,
    client_id                BIGINT UNSIGNED NOT NULL,
    equipment_id             BIGINT UNSIGNED NOT NULL,
    work_type                ENUM('warranty_repair','planned_maintenance','unplanned_repair','installation') NOT NULL,
    description              TEXT,
    priority                 ENUM('critical','high','medium','low') NOT NULL,
    priority_override_reason VARCHAR(500),
    is_warranty              TINYINT(1) NOT NULL DEFAULT 0,
    status                   ENUM('new','assigned','in_progress','waiting_part','completed','on_review','closed') NOT NULL DEFAULT 'new',
    assigned_engineer_id     BIGINT UNSIGNED,
    sla_reaction_deadline    DATETIME NOT NULL,
    sla_resolution_deadline  DATETIME NOT NULL,
    sla_reaction_violated    TINYINT(1) NOT NULL DEFAULT 0,
    sla_resolution_violated  TINYINT(1) NOT NULL DEFAULT 0,
    template_id              BIGINT UNSIGNED,
    initiator_type           ENUM('client','engineer','system') NOT NULL,
    initiator_id             BIGINT UNSIGNED NOT NULL,
    channel                  ENUM('phone','messenger','web_form','mobile_app') NOT NULL,
    created_by_user_id       BIGINT UNSIGNED NOT NULL,
    client_contact_name      VARCHAR(200),
    client_contact_phone     VARCHAR(20),
    client_desired_deadline  DATE,
    client_stated_priority   ENUM('low','medium','high','critical'),
    is_deleted               TINYINT(1) NOT NULL DEFAULT 0,
    created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ticket_number (ticket_number),
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (assigned_engineer_id) REFERENCES users(id),
    FOREIGN KEY (template_id) REFERENCES work_templates(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    INDEX idx_ticket_status (status),
    INDEX idx_ticket_client (client_id),
    INDEX idx_ticket_engineer (assigned_engineer_id),
    INDEX idx_ticket_sla_reaction (sla_reaction_deadline),
    INDEX idx_ticket_sla_resolution (sla_resolution_deadline)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- FK добавляется после создания tickets (circular dependency workaround)
ALTER TABLE repair_history
    ADD CONSTRAINT fk_repair_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id);

CREATE TABLE IF NOT EXISTS ticket_attachments (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id        BIGINT UNSIGNED NOT NULL,
    file_name        VARCHAR(255) NOT NULL,
    file_data        LONGBLOB NOT NULL COMMENT 'BLOB хранение (ADR-001). Лимит 20 МБ валидируется в FileService.',
    file_size_kb     INT UNSIGNED NOT NULL,
    mime_type        VARCHAR(100) NOT NULL,
    uploaded_by_type ENUM('client','engineer','operator') NOT NULL,
    uploaded_by_id   BIGINT UNSIGNED,
    uploaded_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted       TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    INDEX idx_attach_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS work_acts (
    id                       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id                BIGINT UNSIGNED NOT NULL,
    work_description         TEXT NOT NULL,
    work_date                DATE NOT NULL,
    travel_time_minutes      INT UNSIGNED,
    work_time_minutes        INT UNSIGNED,
    completed_at             DATETIME,
    client_confirmed         TINYINT(1) NOT NULL DEFAULT 0,
    client_confirmed_by_name VARCHAR(255),
    client_confirmed_at      DATETIME,
    client_confirmed_method  ENUM('on_device','email_link','verbal'),
    is_draft                 TINYINT(1) NOT NULL DEFAULT 1
                             COMMENT '1 = черновик, 0 = финально сохранён (BR-F-903)',
    created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_act_ticket (ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS work_act_parts (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    work_act_id BIGINT UNSIGNED NOT NULL,
    part_id     BIGINT UNSIGNED NOT NULL,
    qty         INT UNSIGNED NOT NULL,
    source      ENUM('main','engineer_mobile') NOT NULL DEFAULT 'main',
    FOREIGN KEY (work_act_id) REFERENCES work_acts(id),
    FOREIGN KEY (part_id) REFERENCES spare_parts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS comments (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id        BIGINT UNSIGNED NOT NULL,
    author_type      ENUM('employee','client') NOT NULL,
    author_id        BIGINT UNSIGNED COMMENT 'NULL если author_type=client',
    author_client_id BIGINT UNSIGNED COMMENT 'NULL если author_type=employee',
    body             TEXT NOT NULL,
    type             ENUM('internal','external') NOT NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at        DATETIME,
    is_deleted       TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (author_id) REFERENCES users(id),
    FOREIGN KEY (author_client_id) REFERENCES client_contacts(id),
    INDEX idx_comments_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 6: УВЕДОМЛЕНИЯ (Module 14)
-- ============================================================

CREATE TABLE IF NOT EXISTS notification_settings (
    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT UNSIGNED NOT NULL,
    event_type ENUM(
                   'ticket_assigned_to_me',
                   'ticket_status_changed',
                   'sla_violation',
                   'payment_due',
                   'maintenance_due',
                   'warranty_expiring',
                   'new_comment_on_my_ticket'
               ) NOT NULL,
    channel    ENUM('email','push','in_app') NOT NULL,
    enabled    TINYINT(1) NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_notif_settings (user_id, event_type, channel),
    -- in_app нельзя отключить (BR-F-1400)
    CHECK (NOT (channel = 'in_app' AND enabled = 0)),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED NOT NULL,
    event_type  ENUM(
                    'ticket_assigned_to_me',
                    'ticket_status_changed',
                    'sla_violation',
                    'payment_due',
                    'maintenance_due',
                    'warranty_expiring',
                    'new_comment_on_my_ticket'
                ) NOT NULL,
    title       VARCHAR(200) NOT NULL,
    body        TEXT NOT NULL,
    entity_type VARCHAR(50) COMMENT 'ticket / equipment / ...',
    entity_id   BIGINT UNSIGNED,
    read_at     DATETIME COMMENT 'NULL = не прочитано (ADR-004)',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_notif_user_unread (user_id, read_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- ТРИГГЕРЫ
-- ============================================================

-- Автоматически создаёт строки notification_settings для нового пользователя.
-- Покрывает все 7 типов событий × 3 канала = 21 строка на пользователя.
-- Правило BR-F-1400: in_app нельзя отключить — всегда enabled=1.
-- Telegram (push): включён по умолчанию для событий прямого действия.
DELIMITER //
CREATE TRIGGER trg_user_after_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT IGNORE INTO notification_settings (user_id, event_type, channel, enabled) VALUES
    -- ticket_assigned_to_me
    (NEW.id, 'ticket_assigned_to_me',    'email',   1),
    (NEW.id, 'ticket_assigned_to_me',    'push',    1),
    (NEW.id, 'ticket_assigned_to_me',    'in_app',  1),
    -- ticket_status_changed
    (NEW.id, 'ticket_status_changed',    'email',   1),
    (NEW.id, 'ticket_status_changed',    'push',    1),
    (NEW.id, 'ticket_status_changed',    'in_app',  1),
    -- sla_violation (push=0 по умолчанию — шумный канал)
    (NEW.id, 'sla_violation',            'email',   1),
    (NEW.id, 'sla_violation',            'push',    0),
    (NEW.id, 'sla_violation',            'in_app',  1),
    -- payment_due
    (NEW.id, 'payment_due',              'email',   1),
    (NEW.id, 'payment_due',              'push',    0),
    (NEW.id, 'payment_due',              'in_app',  1),
    -- maintenance_due
    (NEW.id, 'maintenance_due',          'email',   1),
    (NEW.id, 'maintenance_due',          'push',    0),
    (NEW.id, 'maintenance_due',          'in_app',  1),
    -- warranty_expiring
    (NEW.id, 'warranty_expiring',        'email',   1),
    (NEW.id, 'warranty_expiring',        'push',    0),
    (NEW.id, 'warranty_expiring',        'in_app',  1),
    -- new_comment_on_my_ticket
    (NEW.id, 'new_comment_on_my_ticket', 'email',   1),
    (NEW.id, 'new_comment_on_my_ticket', 'push',    1),
    (NEW.id, 'new_comment_on_my_ticket', 'in_app',  1);
END //
DELIMITER ;

-- ============================================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ============================================================

-- Справочник моделей оборудования
INSERT IGNORE INTO equipment_models (name, manufacturer, warranty_period_months) VALUES
    ('Matica XID 580i',           'Matica Technologies', 12),
    ('NCR SelfServ 84',           'NCR Corporation',     24),
    ('Diebold Nixdorf DN 200',    'Diebold Nixdorf',     24),
    ('Nautilus Hyosung MX5600SE', 'Nautilus Hyosung',    12);

-- Администратор по умолчанию.
-- ВАЖНО: пароль-заглушка. Запустить scripts/seed.py для создания
-- реального bcrypt-хеша, либо сменить пароль через API после первого входа.
-- Email: admin@servicedesk.local | Password: ChangeMe123!
INSERT IGNORE INTO users
    (full_name, position, department, phone, email, roles, password_hash, status)
VALUES (
    'Системный администратор',
    'Администратор',
    'IT',
    '+70000000000',
    'admin@servicedesk.local',
    JSON_ARRAY('admin'),
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG',
    'active'
);
