# Развёртывание базы данных

ServiceDesk CRM использует **MySQL 8.0**. Схема — 20 таблиц, управляемых через `scripts/init.sql` (первый запуск) и Alembic (миграции).

---

## Структура скриптов

```
scripts/
├── init.sql                   # DDL всех таблиц + триггер + семена справочников
│                              # Выполняется автоматически Docker'ом при первом старте
├── seed.py                    # Python-скрипт: bcrypt-хэши паролей + полные справочники
└── sql/
    ├── 01_equipment_models.sql  # 18 моделей оборудования
    ├── 02_spare_parts.sql       # 60+ запчастей
    ├── 03_initial_users.sql     # 7 стартовых пользователей (placeholder-хэши!)
    └── 04_demo_clients.sql      # 5 демо-клиентов + контакты
```

> **Важно:** `scripts/sql/03_initial_users.sql` содержит placeholder-хэши паролей — они НЕ работают для входа.
> Используйте `scripts/seed.py` для генерации реальных bcrypt-хэшей.

---

## Вариант 1 — Docker (рекомендуется)

### Первый запуск

```bash
# 1. Скопировать .env
cp backend/.env.example backend/.env
# Отредактировать: MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, SECRET_KEY

# 2. Поднять MySQL
docker-compose up -d mysql

# 3. Дождаться готовности (healthcheck: mysqladmin ping)
docker-compose ps   # статус mysql должен быть "healthy"

# 4. Схема применяется автоматически из scripts/init.sql
# Проверить:
docker compose exec mysql mysql -u sduser -psdpass servicedesk \
  -e "SHOW TABLES; SELECT COUNT(*) as users FROM users;"
```

### Загрузка данных

```bash
# Вариант А — Python (реальные bcrypt-хэши, рекомендуется)
docker compose exec backend python /app/../scripts/seed.py

# Вариант Б — SQL-скрипты по порядку (placeholder-хэши)
docker compose exec mysql mysql -u sduser -psdpass servicedesk \
  < scripts/sql/01_equipment_models.sql
docker compose exec mysql mysql -u sduser -psdpass servicedesk \
  < scripts/sql/02_spare_parts.sql
docker compose exec mysql mysql -u sduser -psdpass servicedesk \
  < scripts/sql/03_initial_users.sql
docker compose exec mysql mysql -u sduser -psdpass servicedesk \
  < scripts/sql/04_demo_clients.sql
```

---

## Вариант 2 — Локальная MySQL

### Требования
- MySQL 8.0+ (локально или через WSL)
- Пользователь `sduser` с доступом к БД `servicedesk`

### Установка

```sql
-- Войти как root
mysql -u root -p

-- Создать БД и пользователя
CREATE DATABASE servicedesk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sduser'@'localhost' IDENTIFIED BY 'sdpass';
GRANT ALL PRIVILEGES ON servicedesk.* TO 'sduser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Применить схему

```bash
mysql -u sduser -psdpass servicedesk < scripts/init.sql
```

### Загрузить данные

```bash
# Убедиться, что virtualenv активирован и зависимости установлены
pip install sqlalchemy pymysql passlib[bcrypt]

# Запустить seed.py
python scripts/seed.py
```

---

## Переменные окружения (БД)

| Переменная | Пример | Описание |
|------------|--------|----------|
| `MYSQL_ROOT_PASSWORD` | `rootpass` | Пароль root (только Docker) |
| `MYSQL_DATABASE` | `servicedesk` | Имя базы данных |
| `MYSQL_USER` | `sduser` | Пользователь приложения |
| `MYSQL_PASSWORD` | `sdpass` | Пароль пользователя |
| `DATABASE_URL` | `mysql+pymysql://sduser:sdpass@mysql:3306/servicedesk` | URL для SQLAlchemy / Alembic |

---

## Миграции Alembic

После первого `init.sql` дальнейшие изменения схемы управляются через Alembic.

```bash
# Применить все миграции
docker compose exec backend alembic upgrade head

# Создать новую миграцию
docker compose exec backend alembic revision --autogenerate -m "add new table"

# Откатить последнюю
docker compose exec backend alembic downgrade -1

# Текущая версия
docker compose exec backend alembic current
```

---

## Таблицы БД (20 штук)

| Волна | Таблицы | Назначение |
|-------|---------|-----------|
| 1 — Справочники | `equipment_models`, `clients`, `vendors` | Нет внешних FK |
| 2 — Пользователи | `users`, `client_contacts` | Зависят от clients |
| 3 — Оборудование | `equipment` | → clients, equipment_models |
| 4 — Заявки | `work_templates`, `work_template_steps`, `tickets` | → equipment, users |
| 5 — Детали заявок | `ticket_comments`, `ticket_files`, `work_acts` | → tickets |
| 6 — Склад | `spare_parts` | → vendors |
| 7 — Документы | `invoices`, `invoice_items` | → clients, tickets |
| 8 — История | `repair_history` | → tickets, equipment, users |
| 9 — Уведомления | `notification_settings`, `notifications` | → users |
| 10 — Аудит | `audit_log` | → users |

---

## Ключевые ограничения и триггеры

### Триггер `trg_user_after_insert`
Срабатывает после INSERT в `users`. Автоматически создаёт **21 запись** в `notification_settings`
(7 типов событий × 3 канала: email, push, in_app). Канал `in_app` всегда `enabled=1` и
защищён CHECK-ограничением на уровне БД.

### CHECK-ограничение `chk_no_disable_in_app`
```sql
CONSTRAINT chk_no_disable_in_app
  CHECK NOT (channel = 'in_app' AND enabled = 0)
```
Не даёт отключить in_app уведомления ни через API, ни напрямую в БД.

### Soft Delete
Таблицы с `is_deleted TINYINT(1)`: `users`, `clients`, `equipment`.
Физическое удаление строк не производится — только `is_deleted = 1`.

---

## Резервное копирование

```bash
# Создать дамп
docker compose exec mysql mysqldump \
  -u sduser -psdpass \
  --single-transaction \
  --routines --triggers \
  servicedesk > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить
mysql -u sduser -psdpass servicedesk < backup_20260328_120000.sql
```

---

## Проверка работоспособности

```bash
# Количество строк по ключевым таблицам
docker compose exec mysql mysql -u sduser -psdpass servicedesk -e "
  SELECT 'users' as tbl, COUNT(*) as cnt FROM users WHERE is_deleted=0
  UNION ALL
  SELECT 'equipment_models', COUNT(*) FROM equipment_models
  UNION ALL
  SELECT 'spare_parts', COUNT(*) FROM spare_parts
  UNION ALL
  SELECT 'clients', COUNT(*) FROM clients WHERE is_deleted=0
  UNION ALL
  SELECT 'notification_settings', COUNT(*) FROM notification_settings;
"
```

Ожидаемый результат после `seed.py`:
- `users` ≥ 7
- `equipment_models` ≥ 13
- `spare_parts` ≥ 60
- `clients` ≥ 5
- `notification_settings` = users × 21
