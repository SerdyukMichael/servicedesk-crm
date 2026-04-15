# Ticket Reopen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить переходы `closed → in_progress` и `completed → in_progress` (возобновление заявки), с ограничением по ролям, записью в историю статусов и email-уведомлениями участникам.

**Architecture:** Правила переходов хранятся в `_TRANSITIONS` в `tickets.py`; добавляем `in_progress` в ключи `closed` и `completed`. Ролевая проверка реализуется отдельным guard-блоком внутри `change_ticket_status`. Email отправляется через FastAPI `BackgroundTasks` + `smtplib` (вспомогательный модуль `app/core/email.py`). Если SMTP не настроен — функция возвращает без действий.

**Tech Stack:** Python 3.11, FastAPI BackgroundTasks, smtplib (stdlib), pytest, React + TypeScript

---

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/api/endpoints/tickets.py` | Modify: `_TRANSITIONS`, guard для reopen-ролей, сброс `closed_at`, вызов email |
| `backend/app/core/email.py` | Create: утилита отправки SMTP-письма |
| `backend/tests/test_ticket_reopen.py` | Create: тесты нового поведения |
| `frontend/src/pages/TicketDetailPage.tsx` | Modify: `STATUS_TRANSITIONS`, роль-гейт для кнопки возобновления |
| `docs/sa/API_Specification.yaml` | Modify: описание нового перехода и RBAC |
| `docs/ServiceDesk_CRM_BRD_v1.1.md` | Modify: новое бизнес-требование BR-F-125 |
| `docs/RTM.md` | Modify: строка трассировки для BR-F-125 |

---

## Task 1: Backend — разрешить переход и ограничить по ролям

**Files:**
- Modify: `backend/app/api/endpoints/tickets.py:88-97` (`_TRANSITIONS`)
- Modify: `backend/app/api/endpoints/tickets.py:284-345` (`change_ticket_status`)

- [ ] **Step 1: Добавить `in_progress` в `_TRANSITIONS["closed"]`**

В `tickets.py` строка 96:
```python
_TRANSITIONS = {
    "new":          ["assigned", "cancelled"],
    "assigned":     ["in_progress", "cancelled"],
    "in_progress":  ["waiting_part", "on_review", "completed"],
    "waiting_part": ["in_progress", "cancelled"],
    "on_review":    ["completed", "in_progress"],
    "completed":    ["closed", "in_progress"],
    "closed":       ["in_progress"],   # ← добавлено
    "cancelled":    [],
}
```

- [ ] **Step 2: Добавить набор "reopen-ролей" и guard в `change_ticket_status`**

После строки с `_STATUS_ROLES` (строка 282) добавить константу:
```python
# Роли, которым разрешено возобновлять заявку (closed/completed → in_progress)
_REOPEN_ROLES = frozenset({"admin", "svc_mgr", "client_user"})
```

Внутри `change_ticket_status`, после блока проверки допустимости перехода (после строки `if data.status not in allowed`), добавить guard:
```python
# BR-F-125: возобновление доступно только admin / svc_mgr / client_user
_REOPEN_SOURCES = {"closed", "completed"}
if data.status == "in_progress" and ticket.status in _REOPEN_SOURCES:
    user_roles = set(_get_user_roles(current_user))
    if not user_roles & _REOPEN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN",
                "message": "Возобновить заявку могут только администратор, менеджер или клиент",
            },
        )
```

- [ ] **Step 3: Сбросить `closed_at` при возобновлении**

В блоке обновления статуса, после `ticket.status = data.status` (строка ~313):
```python
# сброс closed_at при возобновлении заявки
if data.status == "in_progress" and prev_status in ("closed", "completed"):
    ticket.closed_at = None
```

- [ ] **Step 4: Проверить тесты вручную (пока email не подключён)**

```bash
docker compose exec backend pytest tests/ -v -k "ticket" 2>&1 | tail -20
```
Ожидаем: все существующие тесты зелёные.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/api/endpoints/tickets.py
git commit -m "feat: BR-F-125 — allow reopen (closed/completed → in_progress) with role guard"
```

---

## Task 2: Email-утилита

**Files:**
- Create: `backend/app/core/email.py`

- [ ] **Step 1: Написать `app/core/email.py`**

```python
"""
Минимальная SMTP-утилита для отправки уведомлений.
Если smtp_host не задан — ничего не делает (graceful no-op).
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_addresses: List[str], subject: str, body_html: str) -> None:
    """Отправить HTML-письмо через SMTP. Если SMTP не настроен — пропустить."""
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.debug("SMTP не настроен, письмо пропущено: %s", subject)
        return

    recipients = [addr for addr in to_addresses if addr]
    if not recipients:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.smtp_user, recipients, msg.as_string())
        logger.info("Email отправлен: %s → %s", subject, recipients)
    except Exception:
        logger.exception("Ошибка отправки email: %s → %s", subject, recipients)
```

- [ ] **Step 2: Коммит**

```bash
git add backend/app/core/email.py
git commit -m "feat: add SMTP email utility (graceful no-op if unconfigured)"
```

---

## Task 3: Подключить email к переходу reopen

**Files:**
- Modify: `backend/app/api/endpoints/tickets.py`

- [ ] **Step 1: Импортировать зависимости**

В начало `tickets.py` добавить:
```python
from fastapi import BackgroundTasks
from app.core.email import send_email
```

- [ ] **Step 2: Обновить сигнатуру `change_ticket_status`**

```python
@router.patch("/{ticket_id}/status", response_model=TicketResponse)
@router.post("/{ticket_id}/status", response_model=TicketResponse)
def change_ticket_status(
    ticket_id: int,
    data: TicketStatusChange,
    background_tasks: BackgroundTasks,          # ← добавить
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STATUS_ROLES)),
    client_scope: Optional[int] = Depends(get_client_scope),
):
```

- [ ] **Step 3: Добавить вызов email после `db.commit()` в блоке reopen**

После блока `db.commit()` в конце функции добавить:
```python
# BR-F-125: email-уведомление при возобновлении заявки
if data.status == "in_progress" and prev_status in ("closed", "completed"):
    # Перезагружаем заявку с joined-loads, чтобы получить email-адреса
    fresh = db.query(Ticket).options(
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee),
    ).filter(Ticket.id == ticket_id).first()

    if fresh:
        # Собираем получателей: инициатор + назначенный инженер
        recipients: list[str] = []
        if fresh.creator and fresh.creator.email:
            recipients.append(fresh.creator.email)
        if fresh.assignee and fresh.assignee.email and fresh.assignee.email not in recipients:
            recipients.append(fresh.assignee.email)

        # Пытаемся найти менеджера (admin / svc_mgr) — берём из текущего пользователя,
        # если у него роль svc_mgr или admin
        initiator_roles = set(_get_user_roles(current_user))
        if initiator_roles & {"admin", "svc_mgr"} and current_user.email not in recipients:
            recipients.append(current_user.email)

        subject = f"Заявка {fresh.number} возобновлена"
        body = f"""
<p>Заявка <b>{fresh.number}</b> «{fresh.title}» была возобновлена и переведена в статус <b>В работе</b>.</p>
<p>Инициатор: {current_user.full_name}</p>
<p><a href="https://mikes1.fvds.ru/tickets/{fresh.id}">Открыть заявку</a></p>
"""
        background_tasks.add_task(send_email, recipients, subject, body)
```

- [ ] **Step 4: Запустить тесты**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -20
```
Ожидаем: все зелёные.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/api/endpoints/tickets.py
git commit -m "feat: BR-F-125 — send email notification on ticket reopen"
```

---

## Task 4: Тесты

**Files:**
- Create: `backend/tests/test_ticket_reopen.py`

- [ ] **Step 1: Написать тест-файл**

```python
"""
Tests for BR-F-125: ticket reopen (closed/completed → in_progress).
"""
import pytest
from tests.conftest import make_admin, make_engineer, make_client, make_equipment_model, make_equipment


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_ticket(client, db, status="closed"):
    from app.models import Ticket
    from datetime import datetime
    t = Ticket(
        number=f"T-{status}-TEST",
        client_id=client.id,
        created_by=1,  # будет переопределено ниже
        title="Тест возобновления",
        type="repair",
        priority="medium",
        status=status,
    )
    return t


def _create_ticket_via_api(client_http, admin_headers, client_id):
    """Создаёт заявку через API и возвращает её id."""
    resp = client_http.post("/api/v1/tickets", json={
        "client_id": client_id,
        "title": "Reopen test ticket",
        "type": "repair",
        "priority": "medium",
    }, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _change_status(client_http, ticket_id, new_status, headers, comment=None):
    payload = {"status": new_status}
    if comment:
        payload["comment"] = comment
    return client_http.post(f"/api/v1/tickets/{ticket_id}/status", json=payload, headers=headers)


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def closed_ticket_id(client, db, admin_headers, client_obj):
    """Создаёт заявку и доводит её до статуса closed."""
    tid = _create_ticket_via_api(client, admin_headers, client_obj.id)

    # Назначить
    engineer = make_engineer(db)
    client.post(f"/api/v1/tickets/{tid}/assign", json={"engineer_id": engineer.id}, headers=admin_headers)

    # Перевести по цепочке: assigned → in_progress → completed → closed
    for s in ["in_progress", "completed", "closed"]:
        r = _change_status(client, tid, s, admin_headers)
        assert r.status_code == 200, f"transition to {s} failed: {r.text}"

    return tid


@pytest.fixture
def completed_ticket_id(client, db, admin_headers, client_obj):
    """Создаёт заявку и доводит её до статуса completed."""
    tid = _create_ticket_via_api(client, admin_headers, client_obj.id)

    engineer = make_engineer(db)
    client.post(f"/api/v1/tickets/{tid}/assign", json={"engineer_id": engineer.id}, headers=admin_headers)

    for s in ["in_progress", "completed"]:
        r = _change_status(client, tid, s, admin_headers)
        assert r.status_code == 200, f"transition to {s} failed: {r.text}"

    return tid


# ─── tests ────────────────────────────────────────────────────────────────────

class TestReopenFromClosed:
    def test_admin_can_reopen_closed(self, client, closed_ticket_id, admin_headers):
        r = _change_status(client, closed_ticket_id, "in_progress", admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_closed_at_cleared_on_reopen(self, client, closed_ticket_id, admin_headers):
        r = _change_status(client, closed_ticket_id, "in_progress", admin_headers)
        assert r.status_code == 200
        assert r.json()["closed_at"] is None

    def test_engineer_cannot_reopen_closed(self, client, db, closed_ticket_id):
        engineer = make_engineer(db)
        login = client.post("/api/v1/auth/login", json={"email": engineer.email, "password": "Test1234!"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = _change_status(client, closed_ticket_id, "in_progress", headers)
        assert r.status_code == 403

    def test_client_user_can_reopen_closed(self, client, db, closed_ticket_id, client_obj):
        from tests.conftest import make_client_user
        cu = make_client_user(db, client_obj.id)
        login = client.post("/api/v1/auth/login", json={"email": cu.email, "password": "Test1234!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = _change_status(client, closed_ticket_id, "in_progress", headers)
        assert r.status_code == 200

    def test_reopen_recorded_in_history(self, client, closed_ticket_id, admin_headers):
        _change_status(client, closed_ticket_id, "in_progress", admin_headers, comment="Повторная работа")
        r = client.get(f"/api/v1/tickets/{closed_ticket_id}/status-history", headers=admin_headers)
        assert r.status_code == 200
        history = r.json()
        last = history[-1]
        assert last["from_status"] == "closed"
        assert last["to_status"] == "in_progress"
        assert last["comment"] == "Повторная работа"


class TestReopenFromCompleted:
    def test_admin_can_reopen_completed(self, client, completed_ticket_id, admin_headers):
        r = _change_status(client, completed_ticket_id, "in_progress", admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_engineer_cannot_reopen_completed(self, client, db, completed_ticket_id):
        engineer = make_engineer(db)
        login = client.post("/api/v1/auth/login", json={"email": engineer.email, "password": "Test1234!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = _change_status(client, completed_ticket_id, "in_progress", headers)
        assert r.status_code == 403

    def test_svc_mgr_can_reopen_completed(self, client, db, completed_ticket_id):
        from tests.conftest import make_svc_mgr
        mgr = make_svc_mgr(db)
        login = client.post("/api/v1/auth/login", json={"email": mgr.email, "password": "Test1234!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = _change_status(client, completed_ticket_id, "in_progress", headers)
        assert r.status_code == 200


class TestInvalidTransitions:
    def test_cannot_reopen_cancelled(self, client, db, admin_headers, client_obj):
        tid = _create_ticket_via_api(client, admin_headers, client_obj.id)
        _change_status(client, tid, "cancelled", admin_headers)
        r = _change_status(client, tid, "in_progress", admin_headers)
        assert r.status_code == 400
        assert r.json()["detail"]["error"] == "BR_VIOLATION"
```

- [ ] **Step 2: Проверить, что нужные фабрики есть в conftest.py**

Если `make_client_user` или `make_svc_mgr` отсутствуют — добавить в `tests/conftest.py`:
```python
def make_client_user(db: Session, client_id: int) -> User:
    u = User(
        email=f"client_user_{uuid4().hex[:6]}@test.local",
        full_name="Client User",
        password_hash=get_password_hash("Test1234!"),
        roles=["client_user"],
        is_active=True,
        client_id=client_id,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def make_svc_mgr(db: Session) -> User:
    u = User(
        email=f"svc_mgr_{uuid4().hex[:6]}@test.local",
        full_name="Service Manager",
        password_hash=get_password_hash("Test1234!"),
        roles=["svc_mgr"],
        is_active=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u
```

- [ ] **Step 3: Запустить тесты**

```bash
docker compose exec backend pytest tests/test_ticket_reopen.py -v
```
Ожидаем: все тесты PASSED.

- [ ] **Step 4: Запустить полный сьют**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -5
```
Ожидаем: 0 FAILED.

- [ ] **Step 5: Коммит**

```bash
git add backend/tests/test_ticket_reopen.py backend/tests/conftest.py
git commit -m "test: BR-F-125 — ticket reopen tests (closed/completed → in_progress)"
```

---

## Task 5: Frontend — кнопка «Возобновить»

**Files:**
- Modify: `frontend/src/pages/TicketDetailPage.tsx:29-38` (`STATUS_TRANSITIONS`)

- [ ] **Step 1: Обновить `STATUS_TRANSITIONS`**

```typescript
const STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  new: ['cancelled'],
  assigned: ['in_progress', 'cancelled'],
  in_progress: ['waiting_part', 'on_review', 'cancelled'],
  waiting_part: ['in_progress', 'cancelled'],
  on_review: ['completed', 'in_progress'],
  completed: ['closed', 'in_progress'],   // ← добавлено in_progress
  closed: ['in_progress'],                // ← добавлено
  cancelled: [],
}
```

- [ ] **Step 2: Добавить ролевой фильтр для reopen-перехода**

Найти в `TicketDetailPage.tsx` место где формируется список доступных переходов (строка ~125):
```typescript
const transitions = STATUS_TRANSITIONS[ticket.status] ?? []
```

Заменить на:
```typescript
const REOPEN_ROLES = ['admin', 'svc_mgr', 'client_user'] as const
const canReopen = REOPEN_ROLES.some(r => hasRole(r))

const transitions = (STATUS_TRANSITIONS[ticket.status] ?? []).filter(s => {
  // Переход в in_progress из closed/completed — только privileged роли
  if (
    s === 'in_progress' &&
    (ticket.status === 'closed' || ticket.status === 'completed')
  ) {
    return canReopen
  }
  return true
})
```

- [ ] **Step 3: Добавить метку для кнопки**

В `STATUS_LABELS` (строка ~40 `TicketDetailPage.tsx`) метки уже есть. Убедиться, что кнопка с `in_progress` из `closed`/`completed` будет выглядеть как «Возобновить», а не «В работе». Найти блок рендеринга кнопок статуса и добавить специальный лейбл:

```typescript
const getTransitionLabel = (from: TicketStatus, to: TicketStatus): string => {
  if (to === 'in_progress' && (from === 'closed' || from === 'completed')) {
    return 'Возобновить'
  }
  return STATUS_LABELS[to]
}
```

Использовать `getTransitionLabel(ticket.status, s)` вместо `STATUS_LABELS[s]` в кнопках переходов.

- [ ] **Step 4: Собрать фронтенд и проверить локально**

```bash
docker compose build frontend
docker compose up -d frontend
```

Открыть http://localhost/, перейти на закрытую заявку — убедиться, что кнопка «Возобновить» видна только у admin/svc_mgr/client_user, у инженера — не видна.

- [ ] **Step 5: Коммит**

```bash
git add frontend/src/pages/TicketDetailPage.tsx
git commit -m "feat: BR-F-125 — reopen button in TicketDetailPage (closed/completed → in_progress)"
```

---

## Task 6: Обновление документации (BA + SA)

**Files:**
- Modify: `docs/ServiceDesk_CRM_BRD_v1.1.md` — новое требование BR-F-125
- Modify: `docs/RTM.md` — трассировка BR-F-125
- Modify: `docs/sa/API_Specification.yaml` — описание перехода

- [ ] **Step 1: Добавить BR-F-125 в BRD**

В `docs/ServiceDesk_CRM_BRD_v1.1.md` в раздел с функциональными требованиями (секция «Управление статусами заявок» или аналогичная) добавить:

```markdown
| BR-F-125 | Возобновление заявки | Система должна позволять перевести заявку из статуса «Закрыта» или «Завершена» обратно в статус «В работе». Переход доступен ролям: admin, svc_mgr, client_user. Инженер выполнить переход не может. При переходе система обнуляет дату закрытия, записывает запись в историю статусов и отправляет email-уведомление инициатору и назначенному инженеру. | admin, svc_mgr, client_user | Must | 2026-04-15 |
```

- [ ] **Step 2: Добавить строку трассировки в RTM.md**

```markdown
| BR-F-125 | Возобновление заявки (closed/completed → in_progress) | — | tickets.py _TRANSITIONS + role guard | PATCH /api/v1/tickets/{id}/status | test_ticket_reopen.py | ✅ Реализовано |
```

- [ ] **Step 3: Обновить API_Specification.yaml**

Найти секцию `PATCH /api/v1/tickets/{ticket_id}/status` и добавить описание:

```yaml
# В description эндпоинта добавить:
# BR-F-125: переходы closed→in_progress и completed→in_progress (возобновление)
# доступны только ролям admin, svc_mgr, client_user.
# При возобновлении: closed_at сбрасывается, история обновляется,
# email отправляется инициатору и инженеру.
```

- [ ] **Step 4: Коммит документации**

```bash
git add docs/ServiceDesk_CRM_BRD_v1.1.md docs/RTM.md docs/sa/API_Specification.yaml
git commit -m "docs: BR-F-125 — update BRD, RTM, API spec for ticket reopen"
```

---

## Self-Review

### Покрытие требований

| Требование | Task |
|---|---|
| `closed → in_progress` | Task 1 |
| `completed → in_progress` (уже было в backend, теперь с ролевым guard) | Task 1 |
| История статусов | Существующий код уже пишет в `TicketStatusHistory` — coverage OK |
| RBAC: admin, svc_mgr, client_user | Task 1 (guard) + Task 5 (frontend) |
| Email: инициатор + менеджер + инженер | Task 3 |
| `closed_at` сброс | Task 1, Step 3 |
| Frontend кнопка «Возобновить» | Task 5 |
| BA/SA документы | Task 6 |

### Проверка типов

- `_REOPEN_ROLES` — `frozenset[str]`, совместимо с `_get_user_roles()` → `list[str]`
- `prev_status` в `change_ticket_status` уже объявлена перед изменением статуса ✓
- `BackgroundTasks` добавлен как параметр FastAPI — автоматически инжектируется ✓
- `REOPEN_ROLES as const` в TypeScript корректно сужает тип ✓

### Потенциальные проблемы

1. **`make_client_user` / `make_svc_mgr`**: могут не существовать в `conftest.py` — Task 4 Step 2 покрывает это.
2. **`closed_at` в TicketResponse**: поле должно быть в Pydantic-схеме — проверить `backend/app/schemas/__init__.py`.
3. **SMTP no-op**: если SMTP не настроен, email просто не отправляется — поведение ожидаемое, тесты не зависят от SMTP.
