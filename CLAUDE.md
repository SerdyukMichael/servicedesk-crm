# CLAUDE.md — ServiceDesk CRM

Система автоматизации сервисной компании по обслуживанию банкоматов и платёжного оборудования.

---

## Стек технологий

| Слой | Технология |
|------|-----------|
| БД | MySQL 8.0 |
| Backend | Python 3.11 + FastAPI 0.111 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Аутентификация | JWT (PyJWT) + bcrypt |
| Валидация | Pydantic v2 |
| Frontend | React + TypeScript (Nginx) |
| Контейнеризация | Docker Compose |
| Тесты | pytest + httpx |

---

## Структура проекта

```
servicedesk-crm/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/   # auth, users, clients, equipment, requests, parts, invoices, vendors
│   │   │   ├── router.py    # /api/v1 — агрегирует все роуты
│   │   │   └── deps.py      # зависимости (db session, current_user)
│   │   ├── core/
│   │   │   ├── config.py    # pydantic-settings
│   │   │   ├── database.py  # SQLAlchemy engine + SessionLocal
│   │   │   └── security.py  # JWT, хэширование паролей
│   │   ├── models/          # SQLAlchemy ORM модели
│   │   ├── schemas/         # Pydantic схемы (request/response)
│   │   ├── services/        # Бизнес-логика (планируется)
│   │   └── main.py          # FastAPI app + CORS + роуты
│   ├── alembic/             # Миграции БД
│   ├── tests/
│   └── requirements.txt
├── frontend/                # React SPA (в разработке)
├── scripts/
│   └── init.sql             # Первоначальная схема БД (выполняется Docker'ом)
├── docker-compose.yml
└── .env.example
```

---

## Команды разработки

### Backend (локально)

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
cp .env.example .env              # заполнить DATABASE_URL и SECRET_KEY
alembic upgrade head              # применить миграции
uvicorn app.main:app --reload     # запуск: http://localhost:8000
```

### Тесты

```bash
cd backend
pytest tests/ -v
```

Тесты не блокируют CI/CD (Phase 1). Полное покрытие — Phase 6.

### Docker (полный стек)

```bash
docker-compose up -d mysql                              # только БД
docker-compose up -d --build                            # весь стек
docker compose exec backend alembic upgrade head        # миграции
```

Сервисы:
- Frontend: http://localhost/
- Backend API: http://localhost:8000/docs
- MySQL: localhost:3306

### Frontend

```bash
cd frontend
npm install
npm run build     # → dist/
```

---

## API эндпоинты

Все маршруты с префиксом `/api/v1`:

| Эндпоинт | Модуль | Назначение |
|----------|--------|-----------|
| `/auth` | auth | Логин, JWT токены |
| `/users` | users | Управление пользователями |
| `/clients` | clients | CRM — клиентская база |
| `/equipment` | equipment | Оборудование у клиентов |
| `/requests` | requests | Заявки на ремонт / ТО |
| `/parts` | parts | Склад запчастей |
| `/invoices` | invoices | Счета и документы |
| `/vendors` | vendors | Вендоры и поставщики |

Swagger UI: `GET /docs` | ReDoc: `GET /redoc` | Health: `GET /health`

---

## Модели БД

- `User` — сотрудники (роли: admin, engineer, manager)
- `Client` — организации-клиенты
- `Equipment` — единица оборудования у клиента
- `ServiceRequest` — заявка (ремонт, ТО), назначается инженеру
- `SparePart` — склад запчастей
- `Invoice` — счёт/документ
- `Vendor` — поставщик
- `Interaction` — история контактов с клиентом

---

## Переменные окружения

Скопировать `.env.example` → `.env` и заполнить:

```
MYSQL_ROOT_PASSWORD   # пароль root MySQL
MYSQL_DATABASE        # servicedesk
MYSQL_USER            # servicedesk_user
MYSQL_PASSWORD        # пароль пользователя БД
SECRET_KEY            # python -c "import secrets; print(secrets.token_hex(32))"
ALGORITHM             # HS256
ACCESS_TOKEN_EXPIRE_MINUTES  # 480
DATABASE_URL          # mysql+pymysql://user:pass@localhost:3306/servicedesk
```

---

## Миграции Alembic

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание изменения"

# Применить все миграции
alembic upgrade head

# Откатить последнюю
alembic downgrade -1
```

---

## Соглашения по коду

- **Python**: именование snake_case, модели SQLAlchemy в `models/`, схемы Pydantic в `schemas/`
- **Эндпоинты**: файл на модуль (`clients.py`, `equipment.py`), router с тегами на русском
- **Схемы**: разделять `Base` / `Create` / `Update` / `InDB` / `Response`
- **Зависимости**: `get_db` и `get_current_user` из `api/deps.py`
- **Бизнес-логика**: выносить в `services/`, не держать в эндпоинтах
- **CORS**: в `main.py` сейчас `allow_origins=["*"]` — перед продом заменить на конкретные домены

---

## CI/CD

`.github/workflows/deploy.yml`:
1. **test** — pytest на Ubuntu (не блокирующий)
2. **deploy** — SSH → pull main → `docker compose up -d --build` → `alembic upgrade head`

Secrets: `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`

---

## Фазы разработки

- **Phase 1** (выполнено) — скаффолд, модели, Docker, CI/CD
- **Phase 2** — бизнес-логика CRUD для всех модулей
- **Phase 3** — PDF-отчёты (reportlab уже в зависимостях)
- **Phase 4** — React UI
- **Phase 5** — React Native (мобильное приложение)
- **Phase 6** — тесты, оптимизация, документация

---

## Практики разработки

### Тесты — обязательно

- **Для любой новой функциональности** создаются тесты (pytest, `backend/tests/`).
- **Все тесты всегда зелёные** — перед завершением задачи запустить `pytest tests/ -v` в контейнере и убедиться, что нет FAILED.
- Команда для запуска: `docker compose exec backend pytest tests/ -v`

### Структура тестов

- Фабрики объектов: `make_admin`, `make_engineer`, `make_client`, `make_equipment_model`, `make_equipment` из `tests/conftest.py`.
- Новые фабрики добавлять в `conftest.py`.
- Один класс тестов на эндпоинт/модуль.

### Пагинация

- Все list-эндпоинты возвращают `PaginatedResponse` с полями `items`, `total`, `page`, `size`, `pages`.
- Параметры запроса: `page` (от 1) и `size`. Не использовать `skip`/`limit`/`has_more`.

### Soft delete

- Записи не удаляются физически: `is_deleted = True` (пользователи, оборудование, клиенты, заявки).
- Справочники (модели оборудования, шаблоны, вендоры) — деактивация через `is_active = False`.

### RBAC

- `require_roles(*roles)` из `api/deps.py` — для write-операций.
- Write-роли для оборудования/справочников: `admin`, `svc_mgr`.
- Просмотр — всем авторизованным.
- Row-level фильтрация для `client_user`: `get_client_scope()` из `api/deps.py` — возвращает `client_id` пользователя, `None` для остальных ролей.

---

## Работа с документацией

### Документы, которые ВСЕГДА актуальны (обновлять при каждом изменении)

- `docs/RBAC_Matrix.md` — матрица прав: роли, разрешения, ограничения
- `docs/ER_DataModel.md` — схема БД: таблицы, поля, связи
- `docs/UC-xxx.md` — только **активные / in-progress** use cases
- `docs/CHANGELOG.md` — список изменений версии

Если при реализации фичи изменилась структура БД, роли или бизнес-правила — обновить соответствующие документы до завершения задачи.

### Документы по запросу (не обновлять автоматически)

`RTM.md`, `RACI.md`, `CJM_Client.html`, `BRD`, `Appendix` — обновляются только по явной просьбе пользователя (перед демо, ревью, планированием спринта).

---

## Git — правила

**Коммит и пуш — только по явной команде пользователя.** Никогда не коммитить и не пушить самостоятельно в конце задачи, даже если всё готово.

Деплой фронтенда:

```bash
docker compose build frontend
docker compose up -d frontend
```

Локальный `npm run build` не попадает в контейнер — фронтенд собирается внутри Docker-образа.
