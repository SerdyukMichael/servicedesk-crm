# DB Migrations Guide — ServiceDesk CRM

**Версия:** 1.0 | **Дата:** 27.03.2026
**СУБД:** MySQL 8.0 | **ORM:** SQLAlchemy 2.0 | **Миграции:** Alembic

---

## 1. Быстрый старт

```bash
cd backend
cp .env.example .env          # заполнить DATABASE_URL
alembic upgrade head           # применить все миграции
python scripts/seed.py         # загрузить начальные данные
```

---

## 2. Порядок создания миграций (граф зависимостей)

Таблицы создаются строго в этом порядке — каждый шаг зависит от предыдущего:

```
Волна 1 — справочники (нет FK наружу)
  M001_create_equipment_models
  M002_create_clients
  M003_create_spare_parts

Волна 2 — пользователи
  M004_create_users                   (зависит от: —)
  M005_create_client_contacts         (зависит от: clients)

Волна 3 — персонал
  M006_create_engineer_competencies   (зависит от: users, equipment_models)
  M007_create_absences                (зависит от: users)
  M008_create_audit_log               (зависит от: users)

Волна 4 — оборудование
  M009_create_equipment               (зависит от: equipment_models, clients)
  M010_create_equipment_documents     (зависит от: equipment, users)
  M011_create_equipment_history       (зависит от: equipment, clients, users)
  M012_create_maintenance_schedules   (зависит от: equipment, users)

Волна 5 — заявки и работа с ними
  M014_create_work_templates          (зависит от: equipment_models, users)
  M015_create_tickets                 (зависит от: clients, equipment, users, work_templates)
  M016_create_ticket_attachments      (зависит от: tickets)
  M017_create_work_acts               (зависит от: tickets)
  M018_create_work_act_parts          (зависит от: work_acts, spare_parts)
  M019_create_comments                (зависит от: tickets, users, client_contacts)

Волна 6 — уведомления
  M020_create_notification_settings   (зависит от: users)
  M021_create_notifications           (зависит от: users)

Волна 7 — настройки и финансы
  M022_create_exchange_rates          (зависит от: users)
```

---

## 3. Полная SQL-схема (init.sql)

> Файл также находится в `scripts/init.sql` — выполняется при старте MySQL-контейнера.

```sql
-- ============================================================
-- НАСТРОЙКИ
-- ============================================================
SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ============================================================
-- ВОЛНА 1: СПРАВОЧНИКИ
-- ============================================================

CREATE TABLE equipment_models (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(200) NOT NULL,
    manufacturer            VARCHAR(200),
    warranty_period_months  INT UNSIGNED NOT NULL DEFAULT 12,
    is_deleted              TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_model_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE clients (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    contract_type       ENUM('premium','standard','none') NOT NULL DEFAULT 'none',
    contract_number     VARCHAR(100),
    contract_valid_until DATE,
    address             VARCHAR(500),
    is_deleted          TINYINT(1) NOT NULL DEFAULT 0,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_client_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE spare_parts (
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

CREATE TABLE users (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(200) NOT NULL,
    position        VARCHAR(100) NOT NULL,
    department      VARCHAR(100) NOT NULL,
    phone           VARCHAR(20) NOT NULL,
    email           VARCHAR(150) NOT NULL,
    hire_date       DATE,
    status          ENUM('active','on_leave','dismissed') NOT NULL DEFAULT 'active',
    roles           JSON NOT NULL COMMENT 'Array of role strings',
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    is_deleted      TINYINT(1) NOT NULL DEFAULT 0,
    password_hash   VARCHAR(255) NOT NULL,
    telegram_chat_id VARCHAR(50) COMMENT 'Telegram chat_id для уведомлений',
    invited_at      DATETIME,
    last_login_at   DATETIME,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE client_contacts (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    client_id       BIGINT UNSIGNED NOT NULL,
    name            VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    email           VARCHAR(150),
    password_hash   VARCHAR(255) COMMENT 'NULL = нет доступа к порталу',
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_contact_email (email),
    FOREIGN KEY (client_id) REFERENCES clients(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 3: ПЕРСОНАЛ
-- ============================================================

CREATE TABLE engineer_competencies (
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

CREATE TABLE absences (
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

CREATE TABLE audit_log (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED COMMENT 'NULL = system action',
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
    -- Нет FK на users намеренно: лог должен хранить запись даже после удаления пользователя
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 4: ОБОРУДОВАНИЕ
-- ============================================================

CREATE TABLE equipment (
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
                        COMMENT 'Пересчитывается Celery-задачей раз в сутки',
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

CREATE TABLE equipment_documents (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_id    BIGINT UNSIGNED NOT NULL,
    doc_type        ENUM('passport','warranty','manual','act','other') NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    file_data       LONGBLOB NOT NULL COMMENT 'Файл хранится как BLOB (ADR-001)',
    file_size_kb    INT UNSIGNED NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    uploaded_by     BIGINT UNSIGNED NOT NULL,
    uploaded_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted      TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
    INDEX idx_equip_docs (equipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE equipment_history (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_id        BIGINT UNSIGNED NOT NULL,
    event_type          ENUM('initial_assignment','transfer','return','write_off') NOT NULL,
    from_client_id      BIGINT UNSIGNED,
    to_client_id        BIGINT UNSIGNED,
    return_type         ENUM('warranty_replacement','buyback'),
    return_date         DATE,
    reason              TEXT,
    claim_created       TINYINT(1) NOT NULL DEFAULT 0,
    recorded_by         BIGINT UNSIGNED NOT NULL,
    recorded_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (from_client_id) REFERENCES clients(id),
    FOREIGN KEY (to_client_id) REFERENCES clients(id),
    FOREIGN KEY (recorded_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE maintenance_schedules (
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

-- ============================================================
-- ВОЛНА 5: ЗАЯВКИ
-- ============================================================

CREATE TABLE work_templates (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    equipment_model_id  BIGINT UNSIGNED NOT NULL,
    work_items          JSON NOT NULL COMMENT '[{"seq":1,"description":"..."}]',
    parts               JSON COMMENT '[{"part_id":1,"qty":2}]',
    created_by          BIGINT UNSIGNED NOT NULL,
    is_deleted          TINYINT(1) NOT NULL DEFAULT 0,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_model_id) REFERENCES equipment_models(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tickets (
    id                          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_number               VARCHAR(20) NOT NULL,
    client_id                   BIGINT UNSIGNED NOT NULL,
    equipment_id                BIGINT UNSIGNED NOT NULL,
    work_type                   ENUM('warranty_repair','planned_maintenance','unplanned_repair','installation') NOT NULL,
    description                 TEXT,
    priority                    ENUM('critical','high','medium','low') NOT NULL,
    priority_override_reason    VARCHAR(500),
    is_warranty                 TINYINT(1) NOT NULL DEFAULT 0,
    status                      ENUM('new','assigned','in_progress','waiting_part','completed','on_review','closed') NOT NULL DEFAULT 'new',
    assigned_engineer_id        BIGINT UNSIGNED,
    sla_reaction_deadline       DATETIME NOT NULL,
    sla_resolution_deadline     DATETIME NOT NULL,
    sla_reaction_violated       TINYINT(1) NOT NULL DEFAULT 0,
    sla_resolution_violated     TINYINT(1) NOT NULL DEFAULT 0,
    template_id                 BIGINT UNSIGNED,
    initiator_type              ENUM('client','engineer','system') NOT NULL,
    initiator_id                BIGINT UNSIGNED NOT NULL,
    channel                     ENUM('phone','messenger','web_form','mobile_app') NOT NULL,
    created_by_user_id          BIGINT UNSIGNED NOT NULL,
    client_contact_name         VARCHAR(200),
    client_contact_phone        VARCHAR(20),
    client_desired_deadline     DATE,
    client_stated_priority      ENUM('low','medium','high','critical'),
    is_deleted                  TINYINT(1) NOT NULL DEFAULT 0,
    created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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

CREATE TABLE ticket_attachments (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id           BIGINT UNSIGNED NOT NULL,
    file_name           VARCHAR(255) NOT NULL,
    file_data           LONGBLOB NOT NULL COMMENT 'BLOB хранение (ADR-001)',
    file_size_kb        INT UNSIGNED NOT NULL,
    mime_type           VARCHAR(100) NOT NULL,
    uploaded_by_type    ENUM('client','engineer','operator') NOT NULL,
    uploaded_by_id      BIGINT UNSIGNED,
    uploaded_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted          TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    INDEX idx_attach_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE work_acts (
    id                          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id                   BIGINT UNSIGNED NOT NULL,
    work_description            TEXT NOT NULL,
    work_date                   DATE NOT NULL,
    travel_time_minutes         INT UNSIGNED,
    work_time_minutes           INT UNSIGNED,
    completed_at                DATETIME,
    client_confirmed            TINYINT(1) NOT NULL DEFAULT 0,
    client_confirmed_by_name    VARCHAR(255),
    client_confirmed_at         DATETIME,
    client_confirmed_method     ENUM('on_device','email_link','verbal'),
    is_draft                    TINYINT(1) NOT NULL DEFAULT 1
                                COMMENT '1=черновик, 0=финально сохранён',
    created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_act_ticket (ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE work_act_parts (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    work_act_id BIGINT UNSIGNED NOT NULL,
    part_id     BIGINT UNSIGNED NOT NULL,
    qty         INT UNSIGNED NOT NULL,
    source      ENUM('main','engineer_mobile') NOT NULL DEFAULT 'main',
    FOREIGN KEY (work_act_id) REFERENCES work_acts(id),
    FOREIGN KEY (part_id) REFERENCES spare_parts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE comments (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id           BIGINT UNSIGNED NOT NULL,
    author_type         ENUM('employee','client') NOT NULL,
    author_id           BIGINT UNSIGNED COMMENT 'NULL если author_type=client',
    author_client_id    BIGINT UNSIGNED COMMENT 'NULL если author_type=employee',
    body                TEXT NOT NULL,
    type                ENUM('internal','external') NOT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at           DATETIME,
    is_deleted          TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (author_id) REFERENCES users(id),
    FOREIGN KEY (author_client_id) REFERENCES client_contacts(id),
    INDEX idx_comments_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ВОЛНА 6: УВЕДОМЛЕНИЯ
-- ============================================================

CREATE TABLE notification_settings (
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
    channel     ENUM('email','push','in_app') NOT NULL,
    enabled     TINYINT(1) NOT NULL DEFAULT 1,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_notif_settings (user_id, event_type, channel),
    -- In-app нельзя отключить (BR-F-1400)
    CHECK (NOT (channel = 'in_app' AND enabled = 0)),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notifications (
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
    read_at     DATETIME COMMENT 'NULL = не прочитано',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_notif_user_unread (user_id, read_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- M022: Курсы валют (BR-F-102, UC-1003)
-- BR-R-206: set_at принимается от клиента (прошедшая/будущая дата); DEFAULT CURRENT_TIMESTAMP — fallback на уровне БД,
--           реальный default подставляется на уровне приложения.
CREATE TABLE exchange_rates (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    currency    VARCHAR(3)       NOT NULL COMMENT 'ISO 4217 код иностранной валюты (USD, EUR...)',
    rate        DECIMAL(15, 4)   NOT NULL COMMENT 'Курс к системной валюте: единиц системной за 1 иностранную',
    set_by      INT UNSIGNED     NOT NULL,
    set_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата курса; может быть прошедшей или будущей (BR-R-206)',
    CONSTRAINT fk_er_set_by FOREIGN KEY (set_by) REFERENCES users(id),
    INDEX idx_er_currency_set_at (currency, set_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='История курсов иностранных валют к системной валюте. Запись с наибольшим set_at по currency = актуальный курс.';
```

---

## 4. Alembic — работа с миграциями

### Инициализация (один раз)
```bash
cd backend
alembic init alembic          # уже выполнено в Phase 1
# alembic.ini: sqlalchemy.url = ${DATABASE_URL}
```

### Создать новую миграцию
```bash
alembic revision --autogenerate -m "create_users_table"
# Файл создаётся в alembic/versions/
# ВСЕГДА проверять автосгенерированный файл перед применением!
```

### Применить все миграции
```bash
alembic upgrade head
```

### Откатить последнюю
```bash
alembic downgrade -1
```

### Посмотреть текущую версию
```bash
alembic current
alembic history --verbose
```

### Правила именования миграций
```
YYYYMMDD_HHMM_описание_через_underscore.py
# Пример: 20260327_1000_create_users_table.py
```

---

## 5. Настройка alembic/env.py

```python
# alembic/env.py — ключевые изменения
from app.models import Base  # импорт всех моделей для autogenerate
from app.core.config import settings

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

---

## 6. Seed-данные (scripts/seed.py)

```python
"""
Запуск: python scripts/seed.py
Загружает начальные данные после применения миграций.
"""

EQUIPMENT_MODELS = [
    {"name": "Matica XID 580i", "manufacturer": "Matica Technologies", "warranty_period_months": 12},
    {"name": "NCR SelfServ 84", "manufacturer": "NCR Corporation", "warranty_period_months": 24},
    {"name": "Diebold Nixdorf DN 200", "manufacturer": "Diebold Nixdorf", "warranty_period_months": 24},
    {"name": "Nautilus Hyosung MX5600SE", "manufacturer": "Nautilus Hyosung", "warranty_period_months": 12},
]

# Матрица notification_settings по умолчанию
# Для каждого нового пользователя при создании (UserService.create):
DEFAULT_NOTIFICATION_SETTINGS = [
    # event_type                    email  push   in_app
    ("ticket_assigned_to_me",       True,  True,  True),
    ("ticket_status_changed",       True,  True,  True),
    ("sla_violation",               True,  False, True),
    ("payment_due",                 True,  False, True),
    ("maintenance_due",             True,  False, True),
    ("warranty_expiring",           True,  False, True),
    ("new_comment_on_my_ticket",    True,  True,  True),
]

# Стандартный Администратор (создаётся один раз)
ADMIN_USER = {
    "full_name": "Системный администратор",
    "email": "admin@servicedesk.local",
    "position": "Администратор",
    "department": "IT",
    "phone": "+70000000000",
    "roles": ["admin"],
    "password": "ChangeMe123!",  # ОБЯЗАТЕЛЬНО сменить после первого входа
}
```

---

## 7. Rollback-стратегия

| Ситуация | Действие |
| --- | --- |
| Ошибка при `upgrade` | `alembic downgrade -1`, исправить миграцию, повторить |
| Критичная ошибка на проде | Восстановить backup БД + откатить деплой |
| Нужно изменить тип поля | Создать новую миграцию (ALTER TABLE), не редактировать существующую |
| Конфликт версий в команде | `alembic merge heads` — слить ветки |

> **Правило:** никогда не редактировать уже применённую миграцию — только создавать новую.

---

## 8. Индексы производительности

Критичные индексы (добавлены в schema):

| Таблица | Индекс | Причина |
| --- | --- | --- |
| `tickets` | `(status)` | Фильтрация по статусу — основной запрос в UC-909 |
| `tickets` | `(assigned_engineer_id)` | Инженер видит только свои заявки |
| `tickets` | `(sla_reaction_deadline)` | Celery SLA-checker — каждые 5 мин |
| `audit_log` | `(entity, entity_id)` | Быстрый поиск истории изменений |
| `audit_log` | `(created_at)` | Фильтрация по периоду (UC-806) |
| `notifications` | `(user_id, read_at)` | Polling непрочитанных — каждые 30 сек |
| `equipment` | `(serial_number)` | UNIQUE + частый поиск (UC-1005) |
