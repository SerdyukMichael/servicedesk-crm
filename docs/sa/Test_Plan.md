# Test Plan — ServiceDesk CRM

**Версия:** 1.0 | **Дата:** 27.03.2026 | **Автор:** Solution Architect

> Документ описывает стратегию тестирования, инструменты, уровни покрытия и правила CI.
> Стек: pytest + httpx + factory_boy + pytest-asyncio. Фаза полного покрытия — Phase 6.
> Phase 1 MVP: smoke-тесты + integration-тесты критического пути.

---

## 1. Стратегия тестирования

### Три уровня

| Уровень | Инструмент | Что тестирует | Целевое покрытие (Phase 6) |
|---|---|---|---|
| **Unit** | pytest | Бизнес-логика сервисов (без БД) | 80% строк в `services/` |
| **Integration** | pytest + httpx + реальная БД | API эндпоинты end-to-end | 70% эндпоинтов |
| **E2E / Smoke** | pytest (подмножество integration) | Критический путь через все слои | 20 обязательных кейсов |

### Принципы

- **Реальная БД**: integration тесты работают с MySQL тестовой БД, не с mock. Причина: mock и prod могут расходиться при изменении схемы.
- **Изоляция**: каждый тест начинается с чистого состояния (транзакция откатывается или таблицы усекаются).
- **Детерминизм**: тесты не зависят от порядка выполнения.
- **Скорость**: unit-тесты < 100 мс каждый, integration < 1 сек.

---

## 2. Инструменты и зависимости

```
# requirements-test.txt
pytest==8.1.0
pytest-asyncio==0.23.0
httpx==0.27.0             # async HTTP-клиент для FastAPI TestClient
factory-boy==3.3.0        # фабрики тестовых данных
Faker==24.0.0             # генерация реалистичных данных
pytest-cov==5.0.0         # покрытие кода
pytest-env==1.1.0         # .env для тестов
```

---

## 3. Конфигурация

### pytest.ini / pyproject.toml

```ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
env = [
    "DATABASE_URL=mysql+pymysql://sduser:sdpass@localhost:3306/servicedesk_test",
    "SECRET_KEY=test-secret-key-32chars-minimum",
    "REDIS_URL=redis://localhost:6379/15",   # отдельная БД Redis для тестов
]
markers = [
    "smoke: критический путь, запускается в CI на каждый push",
    "integration: полные интеграционные тесты",
    "unit: unit-тесты без БД",
    "slow: тесты > 1 сек (пропускаются в быстром режиме)",
]
```

### conftest.py (корневой)

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

# Тестовый движок
test_engine = create_engine(settings.DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Создаёт все таблицы один раз за сессию."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    """Сессия с откатом транзакции после каждого теста."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    """TestClient с переопределённой зависимостью БД."""
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token(client, db):
    """JWT-токен администратора для тестов."""
    from tests.factories import UserFactory
    user = UserFactory(role='admin', db=db)
    res = client.post('/api/v1/auth/login', json={'email': user.email, 'password': 'testpass123'})
    return res.json()['access_token']

@pytest.fixture
def engineer_token(client, db):
    from tests.factories import UserFactory
    user = UserFactory(role='engineer', db=db)
    res = client.post('/api/v1/auth/login', json={'email': user.email, 'password': 'testpass123'})
    return res.json()['access_token']

@pytest.fixture
def auth_headers(admin_token):
    return {'Authorization': f'Bearer {admin_token}'}
```

---

## 4. Фабрики тестовых данных (tests/factories.py)

```python
import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from app.models.user import User
from app.models.client import Client
from app.models.equipment import Equipment, EquipmentModel
from app.models.ticket import Ticket
from app.core.security import hash_password

fake = Faker('ru_RU')

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = 'commit'

    email = factory.LazyFunction(lambda: fake.unique.email())
    full_name = factory.LazyFunction(lambda: fake.name())
    role = 'engineer'
    hashed_password = factory.LazyFunction(lambda: hash_password('testpass123'))
    is_active = True
    is_deleted = False

class ClientFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Client
        sqlalchemy_session_persistence = 'commit'

    name = factory.LazyFunction(lambda: fake.company())
    inn = factory.LazyFunction(lambda: fake.numerify('##########'))
    is_deleted = False

class EquipmentModelFactory(SQLAlchemyModelFactory):
    class Meta:
        model = EquipmentModel
        sqlalchemy_session_persistence = 'commit'

    vendor = 'Matica'
    model_name = factory.LazyFunction(lambda: f'XID {fake.numerify("###")}')
    equipment_type = 'card_printer'

class EquipmentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Equipment
        sqlalchemy_session_persistence = 'commit'

    serial_number = factory.LazyFunction(lambda: fake.unique.bothify('SN-????-####'))
    client = factory.SubFactory(ClientFactory)
    model = factory.SubFactory(EquipmentModelFactory)
    warranty_status = 'valid'
    is_deleted = False

class TicketFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Ticket
        sqlalchemy_session_persistence = 'commit'

    ticket_number = factory.LazyFunction(lambda: f'SD-2026-{fake.unique.numerify("######")}')
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=5))
    status = 'new'
    priority = 'medium'
    ticket_type = 'repair'
    client = factory.SubFactory(ClientFactory)
    sla_violated = False
    is_deleted = False
```

---

## 5. Unit-тесты (tests/unit/)

Unit-тесты проверяют бизнес-логику **без обращения к БД**. Для методов, требующих сессии, передаётся `MagicMock`.

### Структура

```
tests/unit/
├── test_sla_service.py
├── test_ticket_service.py
├── test_file_service.py
├── test_notification_service.py
└── test_report_service.py
```

### Пример: SLAService

```python
# tests/unit/test_sla_service.py
from datetime import datetime, timedelta
import pytest
from app.services.sla_service import SLAService
from tests.factories import TicketFactory

service = SLAService()

def test_sla_deadline_critical():
    """Дедлайн критической заявки = created_at + 4 часа."""
    ticket = TicketFactory.build(priority='critical',
                                  created_at=datetime(2026, 3, 27, 9, 0))
    deadline = service.calculate_deadline(ticket)
    assert deadline == datetime(2026, 3, 27, 13, 0)

def test_sla_deadline_low():
    """Дедлайн низкоприоритетной заявки = created_at + 72 часа."""
    ticket = TicketFactory.build(priority='low',
                                  created_at=datetime(2026, 3, 27, 9, 0))
    deadline = service.calculate_deadline(ticket)
    assert deadline == datetime(2026, 3, 30, 9, 0)

@pytest.mark.parametrize("priority,hours", [
    ('critical', 4), ('high', 8), ('medium', 24), ('low', 72)
])
def test_sla_deadlines_all_priorities(priority, hours):
    now = datetime(2026, 3, 27, 12, 0)
    ticket = TicketFactory.build(priority=priority, created_at=now)
    deadline = service.calculate_deadline(ticket)
    assert deadline == now + timedelta(hours=hours)
```

### Пример: FileService — валидация

```python
# tests/unit/test_file_service.py
import pytest
from unittest.mock import MagicMock
from fastapi import UploadFile
from app.services.file_service import FileService
from app.core.exceptions import BusinessRuleError

service = FileService()

def make_upload_file(size_mb: float, content_type: str) -> UploadFile:
    mock = MagicMock(spec=UploadFile)
    mock.size = int(size_mb * 1024 * 1024)
    mock.content_type = content_type
    return mock

def test_file_too_large_raises():
    file = make_upload_file(25, 'application/pdf')
    with pytest.raises(BusinessRuleError) as exc_info:
        service._validate_file(file, 'ticket_attachment')
    assert 'FILE_TOO_LARGE' in str(exc_info.value.detail)

def test_wrong_mime_type_raises():
    file = make_upload_file(5, 'application/x-executable')
    with pytest.raises(BusinessRuleError) as exc_info:
        service._validate_file(file, 'ticket_attachment')
    assert 'UNSUPPORTED_FILE_TYPE' in str(exc_info.value.detail)

def test_valid_pdf_passes():
    file = make_upload_file(5, 'application/pdf')
    # не должно бросать исключение
    service._validate_file(file, 'equipment_document')
```

---

## 6. Integration-тесты (tests/integration/)

Integration-тесты отправляют HTTP-запросы через `TestClient` и проверяют ответы и состояние БД.

### Структура

```
tests/integration/
├── test_auth.py
├── test_users.py
├── test_clients.py
├── test_equipment.py
├── test_tickets.py
├── test_work_templates.py
├── test_files.py
├── test_notifications.py
└── test_reports.py
```

### Пример: tickets

```python
# tests/integration/test_tickets.py
import pytest
from tests.factories import TicketFactory, ClientFactory, UserFactory

@pytest.mark.smoke
def test_create_ticket_success(client, auth_headers, db):
    """POST /tickets создаёт заявку и возвращает ticket_number."""
    c = ClientFactory(db=db)
    res = client.post('/api/v1/tickets', json={
        'title': 'Не работает картридер',
        'priority': 'high',
        'ticket_type': 'repair',
        'client_id': c.id,
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data['ticket_number'].startswith('SD-2026-')
    assert data['status'] == 'new'
    assert data['sla_violated'] == False

@pytest.mark.smoke
def test_list_tickets_returns_200(client, auth_headers, db):
    TicketFactory.create_batch(3, db=db)
    res = client.get('/api/v1/tickets', headers=auth_headers)
    assert res.status_code == 200
    assert 'items' in res.json()
    assert res.json()['total'] >= 3

def test_ticket_status_transition_new_to_in_progress(client, auth_headers, db):
    """Назначение инженера переводит заявку в in_progress."""
    engineer = UserFactory(role='engineer', db=db)
    ticket = TicketFactory(status='new', db=db)
    res = client.patch(f'/api/v1/tickets/{ticket.id}/assign',
                       json={'engineer_id': engineer.id},
                       headers=auth_headers)
    assert res.status_code == 200
    assert res.json()['status'] == 'in_progress'
    assert res.json()['assigned_engineer_id'] == engineer.id

def test_ticket_close_without_act_returns_400(client, auth_headers, db):
    """Закрытие заявки без подписанного акта возвращает 400."""
    ticket = TicketFactory(status='resolved', db=db)
    res = client.patch(f'/api/v1/tickets/{ticket.id}/status',
                       json={'status': 'closed'},
                       headers=auth_headers)
    assert res.status_code == 400
    assert res.json()['error'] == 'TICKET_CLOSE_WITHOUT_ACT'

def test_ticket_not_found_returns_404(client, auth_headers):
    res = client.get('/api/v1/tickets/99999', headers=auth_headers)
    assert res.status_code == 404
    assert res.json()['error'] == 'TICKET_NOT_FOUND'

def test_engineer_sees_only_own_tickets(client, db):
    """Инженер видит только назначенные ему заявки."""
    engineer = UserFactory(role='engineer', db=db)
    other_engineer = UserFactory(role='engineer', db=db)
    TicketFactory(assigned_engineer_id=engineer.id, db=db)
    TicketFactory(assigned_engineer_id=other_engineer.id, db=db)

    res = client.post('/api/v1/auth/login',
                      json={'email': engineer.email, 'password': 'testpass123'})
    token = res.json()['access_token']

    tickets_res = client.get('/api/v1/tickets',
                             headers={'Authorization': f'Bearer {token}'})
    items = tickets_res.json()['items']
    assert all(t['assigned_engineer_id'] == engineer.id for t in items)
```

### Пример: RBAC

```python
# tests/integration/test_users.py
def test_engineer_cannot_create_user(client, db):
    """Инженер не может создавать пользователей (403)."""
    engineer = UserFactory(role='engineer', db=db)
    res = client.post('/api/v1/auth/login',
                      json={'email': engineer.email, 'password': 'testpass123'})
    token = res.json()['access_token']

    create_res = client.post('/api/v1/users', json={
        'email': 'new@example.com',
        'full_name': 'Test User',
        'role': 'engineer',
        'password': 'pass12345',
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_res.status_code == 403

def test_admin_can_create_user(client, auth_headers):
    res = client.post('/api/v1/users', json={
        'email': 'newuser@example.com',
        'full_name': 'Новый Пользователь',
        'role': 'engineer',
        'password': 'pass12345',
    }, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()['email'] == 'newuser@example.com'

def test_cannot_delete_self(client, db):
    """Пользователь не может удалить сам себя."""
    admin = UserFactory(role='admin', db=db)
    res = client.post('/api/v1/auth/login',
                      json={'email': admin.email, 'password': 'testpass123'})
    token = res.json()['access_token']
    del_res = client.delete(f'/api/v1/users/{admin.id}',
                            headers={'Authorization': f'Bearer {token}'})
    assert del_res.status_code == 400
```

---

## 7. Smoke-тест набор (20 кейсов)

Запускаются в CI на каждый push в ветку. Время выполнения < 60 секунд.

```bash
pytest -m smoke -v
```

| # | ID | Тест | Ожидаемый результат |
|---|---|---|---|
| 1 | T-AUTH-001 | `POST /auth/login` — верные данные | 200, access_token |
| 2 | T-AUTH-002 | `POST /auth/login` — неверный пароль | 401, INVALID_CREDENTIALS |
| 3 | T-AUTH-003 | `GET /tickets` без токена | 401, INVALID_TOKEN |
| 4 | T-USR-001 | `POST /users` (admin) | 201, id заполнен |
| 5 | T-USR-002 | `POST /users` (engineer) | 403, FORBIDDEN |
| 6 | T-CLI-001 | `POST /clients` | 201, name совпадает |
| 7 | T-CLI-002 | `GET /clients/{id}` несуществующий | 404 |
| 8 | T-EQP-001 | `POST /equipment` дубликат serial_number | 409, CONFLICT |
| 9 | T-EQP-002 | `GET /equipment/{id}` | 200, serial_number |
| 10 | T-TKT-001 | `POST /tickets` | 201, SD-2026- |
| 11 | T-TKT-002 | `PATCH /tickets/{id}/assign` | 200, status=in_progress |
| 12 | T-TKT-003 | Закрытие без акта | 400, TICKET_CLOSE_WITHOUT_ACT |
| 13 | T-TKT-004 | `GET /tickets` — инженер видит только свои | 200, фильтр работает |
| 14 | T-TPL-001 | `POST /work-templates` без work_items | 400, EMPTY_WORK_TEMPLATE |
| 15 | T-TPL-002 | `POST /work-templates` валидный | 201 |
| 16 | T-TPL-003 | `GET /work-templates?equipment_model_id=N` | 200, только нужные |
| 17 | T-NTF-001 | `GET /notifications/unread` | 200, count >= 0 |
| 18 | T-NTF-002 | `PUT /notifications/settings` отключить in_app | 400, CANNOT_DISABLE_INAPP |
| 19 | T-FILE-001 | Загрузка файла > 20 МБ | 400, FILE_TOO_LARGE |
| 20 | T-HLTH-001 | `GET /health` | 200, status=ok |

---

## 8. CI/CD правила

### GitHub Actions — тестовый job

```yaml
# .github/workflows/deploy.yml (фрагмент)
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_DATABASE: servicedesk_test
          MYSQL_USER: sduser
          MYSQL_PASSWORD: sdpass
          MYSQL_ROOT_PASSWORD: rootpass
        options: --health-cmd="mysqladmin ping" --health-interval=10s
        ports: ["3306:3306"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt -r backend/requirements-test.txt
      - run: cd backend && pytest -m smoke -v --tb=short
        env:
          DATABASE_URL: mysql+pymysql://sduser:sdpass@localhost:3306/servicedesk_test
          SECRET_KEY: ci-test-secret-key-minimum-32-chars
```

### Правила

| Условие | Действие |
|---|---|
| Push в любую ветку | Запустить smoke (20 кейсов) |
| Pull Request в main | Запустить smoke + integration |
| После деплоя на сервер | Запустить smoke на production URL |
| Integration тесты падают | Блокировать merge |
| Smoke тесты падают | Блокировать deploy |

---

## 9. Покрытие кода

```bash
# Запуск с отчётом покрытия
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Минимальный порог Phase 6
pytest tests/ --cov=app --cov-fail-under=70
```

**Целевые показатели Phase 6:**

| Модуль | Цель |
|---|---|
| `services/` | 80% |
| `api/endpoints/` | 70% |
| `core/` | 90% |
| `models/` | 60% |
| **Итого** | **70%** |

---

## 10. Что НЕ тестируется в Phase 1

- Celery-задачи (unit-тесты сервисов покрывают логику; задачи проверяются вручную)
- Email / Telegram отправка (mock в unit, smoke в Phase 6)
- Frontend (E2E — Phase 6)
- Нагрузочное тестирование (Phase 6)
- PDF / XLSX генерация (smoke ручной в Phase 3)
