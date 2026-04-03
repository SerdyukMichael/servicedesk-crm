# Юнит-тесты Backend

Интеграционные тесты FastAPI с использованием SQLite in-memory.
Не требуют Docker, MySQL или Redis — только Python и зависимости.

## Структура

```
backend/tests/
├── conftest.py                # Фикстуры, in-memory DB, фабрики объектов
├── pytest.ini                 # Конфигурация pytest, маркеры
├── test_security.py           # hash_password, verify_password, JWT (18 тестов)
├── test_auth.py               # POST /auth/login, GET /auth/me (13 тестов)
├── test_users.py              # CRUD /users, RBAC, soft-delete (22 теста)
├── test_clients.py            # CRUD /clients, поиск, фильтры (19 тестов)
├── test_tickets.py            # Заявки, SLA, переходы, комментарии, файлы (25 тестов)
├── test_equipment.py          # Оборудование, дубликат serial, история (16 тестов)
├── test_parts.py              # Склад, low_stock, корректировка (14 тестов)
├── test_work_templates.py     # Шаблоны, пустые шаги, RBAC (14 тестов)
├── test_vendors.py            # Поставщики (8 тестов)
├── test_invoices.py           # Счета, send/pay, VAT (14 тестов)
└── test_notifications.py      # Настройки, BR-F-1400, счётчик (16 тестов)
```

**Итого: ~179 тест-кейсов**

## Быстрый старт

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Все тесты
pytest tests/ -v

# Конкретный файл
pytest tests/test_tickets.py -v

# Только RBAC-тесты
pytest tests/ -v -m rbac

# Только бизнес-правила
pytest tests/ -v -m br

# С покрытием
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

## Архитектура

### База данных
- SQLite in-memory (`sqlite:///:memory:`)
- Каждый тест получает свежую БД (scope=`function`)
- FK enforcement включён через `PRAGMA foreign_keys=ON`

### Фикстуры
| Фикстура | Scope | Описание |
|----------|-------|---------|
| `db` | function | Сессия SQLAlchemy + пустая схема |
| `client` | function | FastAPI TestClient с переопределённой БД |

### Фабрики объектов (`conftest.py`)
```python
make_admin(db)              → User с roles=["admin"]
make_svc_mgr(db)            → User с roles=["svc_mgr"]
make_engineer(db)           → User с roles=["engineer"]
make_user(db, roles=[...])  → User с произвольными ролями
make_client(db)             → Client
make_equipment_model(db)    → EquipmentModel
make_equipment(db, ...)     → Equipment
make_ticket(db, ...)        → Ticket
make_spare_part(db, ...)    → SparePart
make_vendor(db)             → Vendor
make_work_template(db)      → WorkTemplate + step

auth_headers(user_id, roles) → dict с Bearer токеном
```

## Маркеры

| Маркер | Описание |
|--------|---------|
| `unit` | Чистые unit-тесты без HTTP |
| `integration` | Тесты с TestClient + SQLite |
| `security` | Auth/JWT тесты |
| `rbac` | Проверки матрицы доступа |
| `br` | Бизнес-правила |
| `neg` | Негативные сценарии |

## Отличие от приёмочных тестов

| Параметр | Unit-тесты (этот каталог) | Приёмочные (tests/acceptance/) |
|----------|--------------------------|-------------------------------|
| БД | SQLite in-memory | MySQL в Docker |
| HTTP клиент | FastAPI TestClient | httpx.Client (реальный HTTP) |
| Изоляция | Полная (каждый тест — новая БД) | Soft-delete + UUID |
| Требования | только Python | docker-compose up |
| Скорость | ~5 сек на все | ~60 сек (smoke) |
| Цель | CI/CD при каждом push | Смоук после деплоя |
