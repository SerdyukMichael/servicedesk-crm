-- ================================================================
-- ServiceDesk CRM — Инициализация базы данных MySQL 8.0
-- Автор: ServiceDesk CRM Project
-- ================================================================

CREATE DATABASE IF NOT EXISTS servicedesk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE servicedesk;

SET FOREIGN_KEY_CHECKS = 0;

-- ──────────────────────────────────────────────────────────────
-- Пользователи системы
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    email         VARCHAR(128) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(128) NOT NULL,
    role          ENUM('admin','manager','engineer') NOT NULL DEFAULT 'engineer',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Вендоры / Поставщики
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vendors (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    country       VARCHAR(64),
    contact_name  VARCHAR(128),
    contact_email VARCHAR(128),
    contact_phone VARCHAR(32),
    website       VARCHAR(255),
    notes         TEXT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Каталог оборудования
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equipment_catalog (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    model          VARCHAR(128),
    category       ENUM('atm','card_printer','other') NOT NULL DEFAULT 'other',
    vendor_id      INT,
    purchase_price DECIMAL(12,2),
    sale_price     DECIMAL(12,2),
    description    TEXT,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL,
    INDEX idx_catalog_category (category),
    INDEX idx_catalog_vendor (vendor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Клиенты
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clients (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    company_name   VARCHAR(255) NOT NULL,
    inn            VARCHAR(12)  UNIQUE,
    kpp            VARCHAR(9),
    legal_address  TEXT,
    actual_address TEXT,
    contact_name   VARCHAR(128),
    contact_phone  VARCHAR(32),
    contact_email  VARCHAR(128),
    manager_id     INT,
    notes          TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_clients_manager (manager_id),
    INDEX idx_clients_inn (inn),
    FULLTEXT INDEX ft_clients_name (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- История взаимодействий с клиентами
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    client_id   INT NOT NULL,
    user_id     INT NOT NULL,
    type        ENUM('call','email','meeting','other') NOT NULL DEFAULT 'other',
    date        DATETIME NOT NULL,
    subject     VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE RESTRICT,
    INDEX idx_interactions_client (client_id),
    INDEX idx_interactions_date   (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Оборудование у клиентов
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS client_equipment (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    client_id       INT NOT NULL,
    catalog_id      INT NOT NULL,
    serial_number   VARCHAR(64) NOT NULL UNIQUE,
    install_date    DATE,
    address         TEXT,
    status          ENUM('active','in_repair','decommissioned') NOT NULL DEFAULT 'active',
    warranty_until  DATE,
    notes           TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id)  REFERENCES clients(id)           ON DELETE RESTRICT,
    FOREIGN KEY (catalog_id) REFERENCES equipment_catalog(id) ON DELETE RESTRICT,
    INDEX idx_equipment_client (client_id),
    INDEX idx_equipment_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Заявки на обслуживание
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS service_requests (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    number       VARCHAR(32) NOT NULL UNIQUE,
    client_id    INT NOT NULL,
    equipment_id INT,
    engineer_id  INT,
    type         ENUM('repair','maintenance','installation') NOT NULL DEFAULT 'repair',
    priority     ENUM('low','normal','high','critical')      NOT NULL DEFAULT 'normal',
    status       ENUM('new','assigned','in_progress','done','closed') NOT NULL DEFAULT 'new',
    description  TEXT NOT NULL,
    resolution   TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    closed_at    DATETIME,
    created_by   INT NOT NULL,
    FOREIGN KEY (client_id)    REFERENCES clients(id)          ON DELETE RESTRICT,
    FOREIGN KEY (equipment_id) REFERENCES client_equipment(id) ON DELETE SET NULL,
    FOREIGN KEY (engineer_id)  REFERENCES users(id)            ON DELETE SET NULL,
    FOREIGN KEY (created_by)   REFERENCES users(id)            ON DELETE RESTRICT,
    INDEX idx_requests_client   (client_id),
    INDEX idx_requests_engineer (engineer_id),
    INDEX idx_requests_status   (status),
    INDEX idx_requests_priority (priority),
    INDEX idx_requests_created  (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Склад запчастей
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS spare_parts (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    part_number  VARCHAR(64),
    catalog_id   INT,
    quantity     INT NOT NULL DEFAULT 0,
    unit         VARCHAR(16)  NOT NULL DEFAULT 'шт',
    cost_price   DECIMAL(10,2),
    sale_price   DECIMAL(10,2),
    min_quantity INT NOT NULL DEFAULT 0,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (catalog_id) REFERENCES equipment_catalog(id) ON DELETE SET NULL,
    INDEX idx_parts_catalog     (catalog_id),
    INDEX idx_parts_part_number (part_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Движение запчастей на складе (приход/расход)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_movements (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    part_id     INT NOT NULL,
    type        ENUM('in','out') NOT NULL,
    quantity    INT NOT NULL,
    unit_price  DECIMAL(10,2),
    request_id  INT,                         -- если расход — привязка к заявке
    order_id    INT,                         -- если приход — привязка к заказу
    notes       VARCHAR(255),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INT NOT NULL,
    FOREIGN KEY (part_id)    REFERENCES spare_parts(id)       ON DELETE RESTRICT,
    FOREIGN KEY (request_id) REFERENCES service_requests(id)  ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)             ON DELETE RESTRICT,
    INDEX idx_movements_part    (part_id),
    INDEX idx_movements_request (request_id),
    INDEX idx_movements_date    (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Счета
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoices (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    number       VARCHAR(32) NOT NULL UNIQUE,
    client_id    INT NOT NULL,
    request_id   INT,
    type         ENUM('service','sale','parts') NOT NULL DEFAULT 'service',
    status       ENUM('draft','sent','paid','cancelled') NOT NULL DEFAULT 'draft',
    issue_date   DATE NOT NULL,
    due_date     DATE,
    total_amount DECIMAL(14,2) NOT NULL DEFAULT 0,
    vat_rate     DECIMAL(5,2)  NOT NULL DEFAULT 20.00,
    vat_amount   DECIMAL(14,2) NOT NULL DEFAULT 0,
    notes        TEXT,
    created_by   INT NOT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id)  REFERENCES clients(id)          ON DELETE RESTRICT,
    FOREIGN KEY (request_id) REFERENCES service_requests(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)            ON DELETE RESTRICT,
    INDEX idx_invoices_client (client_id),
    INDEX idx_invoices_status (status),
    INDEX idx_invoices_date   (issue_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Позиции счёта
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoice_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id  INT NOT NULL,
    description VARCHAR(512) NOT NULL,
    quantity    DECIMAL(10,3) NOT NULL DEFAULT 1,
    unit        VARCHAR(16)   NOT NULL DEFAULT 'шт',
    unit_price  DECIMAL(12,2) NOT NULL,
    total       DECIMAL(14,2) NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    INDEX idx_items_invoice (invoice_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Заказы у вендоров
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_orders (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    number        VARCHAR(32) NOT NULL UNIQUE,
    vendor_id     INT NOT NULL,
    status        ENUM('draft','sent','confirmed','received','cancelled') NOT NULL DEFAULT 'draft',
    order_date    DATE NOT NULL,
    expected_date DATE,
    received_date DATE,
    total_amount  DECIMAL(14,2),
    currency      VARCHAR(3) NOT NULL DEFAULT 'RUB',
    notes         TEXT,
    created_by    INT NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id)  REFERENCES vendors(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id)   ON DELETE RESTRICT,
    INDEX idx_po_vendor (vendor_id),
    INDEX idx_po_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────────
-- Позиции заказа у вендора
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    order_id    INT NOT NULL,
    part_id     INT,
    catalog_id  INT,
    description VARCHAR(512) NOT NULL,
    quantity    INT NOT NULL,
    unit_price  DECIMAL(12,2),
    total       DECIMAL(14,2),
    FOREIGN KEY (order_id)   REFERENCES purchase_orders(id)   ON DELETE CASCADE,
    FOREIGN KEY (part_id)    REFERENCES spare_parts(id)        ON DELETE SET NULL,
    FOREIGN KEY (catalog_id) REFERENCES equipment_catalog(id)  ON DELETE SET NULL,
    INDEX idx_po_items_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;

-- ──────────────────────────────────────────────────────────────
-- Первичные данные: администратор по умолчанию
-- пароль: Admin1234  (bcrypt hash)
-- ──────────────────────────────────────────────────────────────
INSERT IGNORE INTO users (username, email, password_hash, full_name, role)
VALUES (
    'admin',
    'admin@servicedesk.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lek.dMbpPDNd2Xhge',
    'Администратор',
    'admin'
);
