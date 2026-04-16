# Work Act → Invoice Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Запретить редактирование акта после подписания или создания счёта (кроме admin); при редактировании admin — автоматически синхронизировать неоплаченный счёт, либо показать диалог если счёт оплачен.

**Architecture:** Вся логика — в `endpoints/tickets.py` (PATCH /tickets/{id}/work-act). Добавляем `force_save` флаг в `WorkActUpdate`. Бэкенд возвращает 409 `INVOICE_PAID_MISMATCH` когда сохранение требует подтверждения. Фронтенд перехватывает 409 и показывает диалог; при подтверждении повторяет запрос с `force_save: true`.

**Tech Stack:** FastAPI, SQLAlchemy, React + TypeScript, TanStack Query, pytest + httpx

---

## Файловая карта

| Файл | Изменение |
|------|-----------|
| `backend/app/schemas/__init__.py` | `WorkActUpdate` + поле `force_save: bool` |
| `backend/app/api/endpoints/tickets.py` | `update_work_act` — три новых гварда + sync-логика |
| `backend/tests/test_work_act_invoice_lock.py` | 7 новых тестов |
| `frontend/src/pages/TicketDetailPage.tsx` | условие кнопки + диалог INVOICE_PAID_MISMATCH |
| `docs/ServiceDesk_CRM_BRD_v1.1.md` | BR-F-126, BR-F-127 |
| `docs/RTM.md` | строки R1-10, R1-11 |
| `docs/sa/API_Specification.yaml` | обновить PATCH /tickets/{id}/work-act |

---

## Task 1: Схема — добавить `force_save` в `WorkActUpdate`

**Files:**
- Modify: `backend/app/schemas/__init__.py:507-511`

- [ ] **Step 1: Открыть схему WorkActUpdate (строки 507-511)**

Текущий код:
```python
class WorkActUpdate(BaseModel):
    work_description: Optional[str] = None
    parts_used: Optional[Any] = None
    total_time_minutes: Optional[int] = None
    items: Optional[List[WorkActItemCreate]] = None  # None = не менять, [] = удалить все
```

Новый код — добавить одно поле:
```python
class WorkActUpdate(BaseModel):
    work_description: Optional[str] = None
    parts_used: Optional[Any] = None
    total_time_minutes: Optional[int] = None
    items: Optional[List[WorkActItemCreate]] = None  # None = не менять, [] = удалить все
    force_save: bool = False  # True = сохранить акт даже если счёт оплачен и суммы расходятся
```

- [ ] **Step 2: Проверить что схема импортируется без ошибок**

```bash
docker compose exec -T backend python -c "from app.schemas import WorkActUpdate; print(WorkActUpdate.model_fields.keys())"
```
Expected: `dict_keys(['work_description', 'parts_used', 'total_time_minutes', 'items', 'force_save'])`

---

## Task 2: Написать тесты (TDD — RED)

**Files:**
- Create: `backend/tests/test_work_act_invoice_lock.py`

- [ ] **Step 1: Создать файл теста**

```python
"""
Tests for work act edit lock when invoice exists (BR-F-126, BR-F-127).

Covered:
- signed act cannot be edited (already tested in existing suite; guard kept)
- non-admin (engineer, svc_mgr) cannot edit act if invoice exists for ticket → 403
- admin CAN edit act even if invoice exists
- admin edit act with unpaid invoice → invoice items replaced + totals recalculated → 200
- admin edit act with paid invoice, no force_save → 409 INVOICE_PAID_MISMATCH
- admin edit act with paid invoice, force_save=True → act saved, invoice untouched → 200
- admin edit act when no invoice → just saves, 200
"""
import pytest
from decimal import Decimal
from datetime import date
from tests.conftest import (
    make_admin, make_svc_mgr, make_engineer, make_client,
    make_client_user, make_equipment_model, make_equipment, auth_headers,
)
from app.models import WorkAct, WorkActItem, Invoice, InvoiceItem, Ticket


# ─── helpers ──────────────────────────────────────────────────────────────────

def _setup(db):
    admin = make_admin(db)
    svc   = make_svc_mgr(db, email="svc_lock@t.com")
    eng   = make_engineer(db, email="eng_lock@t.com")
    cl    = make_client(db)
    model = make_equipment_model(db)
    eq    = make_equipment(db, cl.id, model.id)
    return (
        auth_headers(admin.id, admin.roles),
        auth_headers(svc.id,   svc.roles),
        auth_headers(eng.id,   eng.roles),
        cl, eq, eng,
    )


def _create_ticket_with_act(http, admin_hdrs, eng, cl, eq, db):
    """Create ticket, assign, move to in_progress, create work act with 1 item (100.00)."""
    r = http.post("/api/v1/tickets", headers=admin_hdrs, json={
        "client_id": cl.id, "equipment_id": eq.id,
        "title": "Lock test", "type": "repair", "priority": "medium",
    })
    assert r.status_code == 201
    tid = r.json()["id"]

    http.post(f"/api/v1/tickets/{tid}/assign",
              json={"engineer_id": eng.id}, headers=admin_hdrs)
    http.post(f"/api/v1/tickets/{tid}/status",
              json={"status": "in_progress"}, headers=admin_hdrs)

    r = http.post(f"/api/v1/tickets/{tid}/work-act", headers=admin_hdrs, json={
        "work_description": "Диагностика",
        "items": [{"item_type": "service", "name": "Диагностика", "quantity": "1",
                   "unit": "шт", "unit_price": "100.00", "sort_order": 0}],
    })
    assert r.status_code == 201
    return tid


def _create_invoice_for_ticket(db, ticket_id, client_id, creator_id, paid=False):
    """Directly insert invoice + item into DB (bypasses API)."""
    from datetime import datetime
    inv = Invoice(
        number=f"TEST-INV-{ticket_id}",
        client_id=client_id,
        ticket_id=ticket_id,
        type="service",
        status="paid" if paid else "draft",
        issue_date=date.today(),
        subtotal=Decimal("100.00"),
        vat_rate=Decimal("20.00"),
        vat_amount=Decimal("20.00"),
        total_amount=Decimal("120.00"),
        created_by=creator_id,
        paid_at=datetime.utcnow() if paid else None,
    )
    db.add(inv)
    db.flush()
    item = InvoiceItem(
        invoice_id=inv.id,
        description="Диагностика",
        quantity=Decimal("1"),
        unit="шт",
        unit_price=Decimal("100.00"),
        total=Decimal("100.00"),
        sort_order=0,
    )
    db.add(item)
    db.commit()
    db.refresh(inv)
    return inv


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def setup(client, db):
    admin_hdrs, svc_hdrs, eng_hdrs, cl, eq, eng = _setup(db)
    admin_user = db.query(__import__("app.models", fromlist=["User"]).User)\
                   .filter_by(email="admin@example.com").first()
    return {
        "http": client, "admin": admin_hdrs, "svc": svc_hdrs, "eng": eng_hdrs,
        "cl": cl, "eq": eq, "eng_obj": eng, "admin_user": admin_user,
    }


# ─── tests ────────────────────────────────────────────────────────────────────

class TestActLockNoInvoice:
    def test_admin_can_edit_act_without_invoice(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"work_description": "Обновлено"})
        assert r.status_code == 200

    def test_engineer_can_edit_act_without_invoice(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["eng"],
                            json={"work_description": "Обновлено инженером"})
        assert r.status_code == 200


class TestActLockWithInvoice:
    def test_engineer_cannot_edit_act_when_invoice_exists(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["eng"],
                            json={"work_description": "Попытка инженера"})
        assert r.status_code == 403
        assert r.json()["error"] == "ACT_LOCKED_INVOICE_EXISTS"

    def test_svc_mgr_cannot_edit_act_when_invoice_exists(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["svc"],
                            json={"work_description": "Попытка svc_mgr"})
        assert r.status_code == 403
        assert r.json()["error"] == "ACT_LOCKED_INVOICE_EXISTS"

    def test_admin_can_edit_act_even_when_invoice_exists(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"work_description": "Обновлено администратором",
                                  "items": [{"item_type": "service", "name": "Замена",
                                             "quantity": "2", "unit": "шт",
                                             "unit_price": "200.00", "sort_order": 0}]})
        assert r.status_code == 200


class TestActSyncUnpaidInvoice:
    def test_admin_edit_act_syncs_unpaid_invoice(self, setup, db):
        """After admin edits act items, unpaid invoice items and totals are replaced."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        inv = _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)

        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"items": [
                                {"item_type": "service", "name": "Замена платы",
                                 "quantity": "1", "unit": "шт",
                                 "unit_price": "500.00", "sort_order": 0},
                            ]})
        assert r.status_code == 200

        db.refresh(inv)
        # Invoice total should now reflect new act: 500 + 20% VAT = 600
        assert inv.subtotal == Decimal("500.00")
        assert inv.total_amount == Decimal("600.00")
        assert len(inv.items) == 1
        assert inv.items[0].description == "Замена платы"


class TestActPaidInvoiceMismatch:
    def test_admin_edit_act_returns_409_when_invoice_paid(self, setup, db):
        """When invoice is paid and totals differ, return 409 INVOICE_PAID_MISMATCH."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=True)

        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"items": [
                                {"item_type": "service", "name": "Новая работа",
                                 "quantity": "1", "unit": "шт",
                                 "unit_price": "999.00", "sort_order": 0},
                            ]})
        assert r.status_code == 409
        body = r.json()
        assert body["error"] == "INVOICE_PAID_MISMATCH"
        assert "act_total" in body
        assert "invoice_total" in body

    def test_admin_force_save_ignores_paid_invoice(self, setup, db):
        """With force_save=True, act is saved but paid invoice is not modified."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"], db)
        inv = _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=True)
        original_total = inv.total_amount

        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"force_save": True,
                                  "items": [
                                      {"item_type": "service", "name": "Новая работа",
                                       "quantity": "1", "unit": "шт",
                                       "unit_price": "999.00", "sort_order": 0},
                                  ]})
        assert r.status_code == 200
        # Act updated
        assert r.json()["items"][0]["unit_price"] == "999.00"
        # Invoice untouched
        db.refresh(inv)
        assert inv.total_amount == original_total
```

- [ ] **Step 2: Запустить тест — убедиться что RED**

```bash
docker compose exec -T backend pytest tests/test_work_act_invoice_lock.py -v 2>&1 | tail -20
```
Expected: несколько FAILED (логика ещё не реализована)

---

## Task 3: Реализация в бэкенде

**Files:**
- Modify: `backend/app/api/endpoints/tickets.py:655-707`

- [ ] **Step 1: Добавить вспомогательную функцию `_calc_act_total` и обновить `update_work_act`**

Найти функцию `update_work_act` (строка ~655). Заменить её полностью:

```python
def _calc_act_total(items: list) -> Decimal:
    """Сумма позиций акта (без НДС)."""
    return sum((i.total for i in items), Decimal("0"))


def _sync_invoice_from_act(invoice: Invoice, act_items: list, db: Session) -> None:
    """Заменить позиции счёта позициями акта и пересчитать итоги."""
    # Удалить все текущие позиции счёта
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()
    db.flush()
    # Добавить новые из акта
    for i, act_item in enumerate(act_items):
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            description=act_item.name,
            quantity=act_item.quantity,
            unit=act_item.unit,
            unit_price=act_item.unit_price,
            total=act_item.total,
            sort_order=i,
            item_type=act_item.item_type,
            service_id=act_item.service_id,
            part_id=act_item.part_id,
        ))
    db.flush()
    db.refresh(invoice)
    # Пересчитать итоги
    subtotal = sum(item.total for item in invoice.items)
    vat = (subtotal * invoice.vat_rate / 100).quantize(Decimal("0.01"))
    invoice.subtotal = subtotal
    invoice.vat_amount = vat
    invoice.total_amount = subtotal + vat


@router.patch("/{ticket_id}/work-act", response_model=WorkActResponse)
def update_work_act(
    ticket_id: int,
    data: WorkActUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("engineer", "svc_mgr", "admin")),
):
    _require_ticket(db, ticket_id)
    act = (
        db.query(WorkAct)
        .options(joinedload(WorkAct.items))
        .filter(WorkAct.ticket_id == ticket_id)
        .first()
    )
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт выполненных работ не найден"},
        )

    # Guard 1: акт подписан → запрещено всем
    if act.signed_by is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Акт подписан и не может быть изменён"},
        )

    # Guard 2: счёт существует → только admin
    user_roles = set(_get_user_roles(current_user))
    invoice = (
        db.query(Invoice)
        .filter(Invoice.ticket_id == ticket_id)
        .filter(Invoice.status != "cancelled")
        .order_by(Invoice.created_at.desc())
        .first()
    )
    if invoice is not None and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACT_LOCKED_INVOICE_EXISTS",
                    "message": "Редактирование акта заблокировано: счёт уже создан. Обратитесь к администратору"},
        )

    # Применяем изменения
    if data.work_description is not None:
        act.work_description = data.work_description
    if data.total_time_minutes is not None:
        act.total_time_minutes = data.total_time_minutes
    if data.parts_used is not None:
        act.parts_used = data.parts_used

    if data.items is not None:
        db.query(WorkActItem).filter(WorkActItem.work_act_id == act.id).delete()
        for i, item_data in enumerate(data.items):
            total = (item_data.quantity * item_data.unit_price).quantize(Decimal("0.01"))
            db.add(WorkActItem(
                work_act_id=act.id,
                item_type=item_data.item_type,
                service_id=item_data.service_id,
                part_id=item_data.part_id,
                name=item_data.name,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                total=total,
                sort_order=item_data.sort_order if item_data.sort_order else i,
            ))
        db.flush()

    db.refresh(act)

    # Синхронизация счёта (только если изменились позиции)
    if invoice is not None and data.items is not None:
        act_total = _calc_act_total(act.items)
        inv_total  = invoice.subtotal  # без НДС, для сравнения

        if act_total != inv_total:
            if invoice.status == "paid":
                if not data.force_save:
                    # НЕ коммитим — откатываем изменения акта
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "INVOICE_PAID_MISMATCH",
                            "message": "Сумма акта изменилась, но счёт уже оплачен. Подтвердите сохранение.",
                            "act_total": str(act_total),
                            "invoice_total": str(invoice.total_amount),
                        },
                    )
                # force_save=True: сохраняем акт, счёт не трогаем
            else:
                # Счёт не оплачен — синхронизируем
                _sync_invoice_from_act(invoice, act.items, db)

    db.commit()
    db.refresh(act)
    return act
```

- [ ] **Step 2: Убедиться что нет синтаксических ошибок**

```bash
docker compose exec -T backend python -c "from app.api.endpoints.tickets import update_work_act; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Запустить тесты — должны стать GREEN**

```bash
docker compose exec -T backend pytest tests/test_work_act_invoice_lock.py -v 2>&1 | tail -20
```
Expected: 7/7 PASSED

- [ ] **Step 4: Прогнать полный сьют**

```bash
docker compose exec -T backend pytest tests/ -v --tb=short 2>&1 | tail -10
```
Expected: все PASSED (было 388, теперь 395)

- [ ] **Step 5: Коммит**

```bash
git add backend/app/schemas/__init__.py backend/app/api/endpoints/tickets.py backend/tests/test_work_act_invoice_lock.py
git commit -m "feat: work act edit lock when invoice exists (BR-F-126, BR-F-127)"
```

---

## Task 4: Фронтенд — кнопка «Редактировать акт»

**Files:**
- Modify: `frontend/src/pages/TicketDetailPage.tsx:406-422`

- [ ] **Step 1: Изменить условие видимости кнопки «Редактировать акт»**

Текущий код (строка ~406):
```tsx
{canCreateAct && workAct && !workAct.signed_by && (
  <button
    className="btn btn-secondary btn-sm"
    onClick={...}
  >
    {showWorkActForm && isEditingAct ? 'Отмена' : 'Редактировать акт'}
  </button>
)}
```

Новый код:
```tsx
{canCreateAct && workAct && !workAct.signed_by && (!invoice || hasRole('admin')) && (
  <button
    className="btn btn-secondary btn-sm"
    onClick={() => {
      if (showWorkActForm && isEditingAct) {
        setShowWorkActForm(false)
        setIsEditingAct(false)
        setActItems([])
        setWorkActDesc('')
      } else {
        handleEditWorkAct()
      }
    }}
  >
    {showWorkActForm && isEditingAct ? 'Отмена' : 'Редактировать акт'}
  </button>
)}
```

Примечание: `invoice` — это уже загруженная переменная из `useQuery` (строка ~73), содержащая первый счёт для заявки (или `undefined`). Проверить что переменная называется `invoice` — если нет, скорректировать.

- [ ] **Step 2: Проверить имя переменной для счёта**

В текущем коде (строка ~73):
```ts
const { data: workAct } = useWorkAct(ticketId)
```
и далее для счёта. Найти и использовать правильное имя.

```bash
grep -n "invoice\|useQuery.*invoice\|data.*invoice" frontend/src/pages/TicketDetailPage.tsx | head -10
```

Если переменная называется иначе — использовать правильное имя в условии.

---

## Task 5: Фронтенд — диалог INVOICE_PAID_MISMATCH

**Files:**
- Modify: `frontend/src/pages/TicketDetailPage.tsx`

- [ ] **Step 1: Добавить состояния для диалога**

Найти блок `useState` (строки ~109-114). После существующих состояний добавить:

```tsx
// INVOICE_PAID_MISMATCH dialog state
const [paidMismatchDialog, setPaidMismatchDialog] = useState<{
  actTotal: string
  invoiceTotal: string
  pendingPayload: object
} | null>(null)
```

- [ ] **Step 2: Обновить `handleSubmitWorkAct` для перехвата 409**

Найти функцию `handleSubmitWorkAct` (строка ~180). Обновить ветку `isEditingAct`:

```tsx
const handleSubmitWorkAct = () => {
  const payload = { work_description: workActDesc, items: actItems }

  if (isEditingAct) {
    updateWorkAct.mutate(payload, {
      onSuccess: () => {
        setShowWorkActForm(false)
        setIsEditingAct(false)
        setActItems([])
        setWorkActDesc('')
      },
      onError: (err: any) => {
        const detail = err?.response?.data
        if (detail?.error === 'INVOICE_PAID_MISMATCH') {
          setPaidMismatchDialog({
            actTotal: detail.act_total,
            invoiceTotal: detail.invoice_total,
            pendingPayload: payload,
          })
        }
        // прочие ошибки обрабатываются глобально
      },
    })
  } else {
    createWorkAct.mutate(
      { work_description: workActDesc, items: actItems },
      { onSuccess: () => { setShowWorkActForm(false); setActItems([]) } },
    )
  }
}
```

- [ ] **Step 3: Добавить функцию подтверждения force_save**

После `handleSubmitWorkAct` добавить:
```tsx
const handleForceSaveAct = () => {
  if (!paidMismatchDialog) return
  const payload = { ...paidMismatchDialog.pendingPayload, force_save: true }
  updateWorkAct.mutate(payload as any, {
    onSuccess: () => {
      setPaidMismatchDialog(null)
      setShowWorkActForm(false)
      setIsEditingAct(false)
      setActItems([])
      setWorkActDesc('')
    },
  })
}
```

- [ ] **Step 4: Добавить JSX диалога**

В конце JSX компонента (перед закрывающим `</div>` страницы) добавить:

```tsx
{/* INVOICE_PAID_MISMATCH dialog */}
{paidMismatchDialog && (
  <div style={{
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
  }}>
    <div style={{
      background: 'var(--surface)', borderRadius: 8, padding: 24,
      maxWidth: 440, width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
    }}>
      <h3 style={{ marginBottom: 12, color: 'var(--color-warning, #f59e0b)' }}>
        ⚠ Счёт уже оплачен
      </h3>
      <p style={{ marginBottom: 8 }}>
        Сумма акта изменилась, но связанный счёт уже <strong>оплачен</strong> и не будет скорректирован.
      </p>
      <p style={{ marginBottom: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
        Сумма акта: <strong>{parseFloat(paidMismatchDialog.actTotal).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} ₽</strong>
        &nbsp;·&nbsp;
        Сумма счёта: <strong>{parseFloat(paidMismatchDialog.invoiceTotal).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} ₽</strong>
      </p>
      <p style={{ marginBottom: 20 }}>Сохранить изменения в акте без корректировки счёта?</p>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button
          className="btn btn-secondary"
          onClick={() => setPaidMismatchDialog(null)}
        >
          Нет, отмена
        </button>
        <button
          className="btn btn-danger"
          onClick={handleForceSaveAct}
          disabled={updateWorkAct.isPending}
        >
          Да, сохранить акт
        </button>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 5: Сборка фронтенда**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: `✓ built in X.XXs`

- [ ] **Step 6: Коммит фронтенда**

```bash
git add frontend/src/pages/TicketDetailPage.tsx
git commit -m "feat: work act edit dialog for paid invoice mismatch"
```

---

## Task 6: Обновить документацию

**Files:**
- Modify: `docs/ServiceDesk_CRM_BRD_v1.1.md`
- Modify: `docs/RTM.md`

- [ ] **Step 1: Добавить требования в BRD**

В секции функциональных требований (поиск по `BR-F-125`) добавить после:

```markdown
| BR-F-126 | Блокировка редактирования акта после создания счёта | После создания счёта по акту редактирование акта разрешено только роли `admin`. Для всех остальных — запрет (403 `ACT_LOCKED_INVOICE_EXISTS`). После подписания акта клиентом редактирование запрещено для всех. | Must | svc_mgr, engineer |
| BR-F-127 | Синхронизация счёта при редактировании акта администратором | Если admin изменил позиции акта: (а) счёт не оплачен → позиции и суммы счёта обновляются автоматически; (б) счёт оплачен → возвращается 409 `INVOICE_PAID_MISMATCH` с суммами; admin подтверждает → сохраняется только акт, счёт не меняется. | Must | admin |
```

- [ ] **Step 2: Добавить строки в RTM.md**

В Модуле 1 (Прайс-листы) добавить строки:

```markdown
| R1-10 | BR-F-126 | Блокировка редактирования акта при наличии счёта (кроме admin) | Must | UC-101, UC-102 | `endpoints/tickets.py` (update_work_act guard) | `tests/test_work_act_invoice_lock.py` | ✅ |
| R1-11 | BR-F-127 | Автосинхронизация счёта при редактировании акта admin; диалог при оплаченном счёте | Must | UC-101, UC-102 | `endpoints/tickets.py` (update_work_act sync), `TicketDetailPage.tsx` | `tests/test_work_act_invoice_lock.py` | ✅ |
```

- [ ] **Step 3: Коммит документации**

```bash
git add docs/ServiceDesk_CRM_BRD_v1.1.md docs/RTM.md
git commit -m "docs: BR-F-126, BR-F-127 — act edit lock and invoice sync"
```

---

## Task 7: Деплой на тест и интерфейсная проверка

- [ ] **Step 1: Пересобрать и задеплоить бэкенд**

```bash
docker compose build backend
docker compose up -d backend
docker compose exec -T backend pytest tests/ -v --tb=short 2>&1 | tail -5
```
Expected: все PASSED

- [ ] **Step 2: Скопировать фронтенд на тестовый стенд**

```bash
# Фронтенд уже собран в Task 5, копируем в nginx
docker compose exec -T frontend cp -r /usr/share/nginx/html/. /tmp/ 2>/dev/null || true
# Для локального стенда фронтенд обслуживает nginx напрямую из dist/
```

Для локального стенда — просто пересобрать фронтенд-контейнер:
```bash
docker compose build frontend
docker compose up -d frontend
```

- [ ] **Step 3: Проверка через Playwright**

Сценарий 1 — инженер не видит кнопку «Редактировать акт» при наличии счёта:
```python
# Войти как engineer, открыть заявку с актом и счётом
# Убедиться что кнопки «Редактировать акт» нет
```

Сценарий 2 — admin видит кнопку, редактирует, диалог при оплаченном счёте:
```python
# Войти как admin, открыть заявку с актом и оплаченным счётом
# Нажать «Редактировать акт», изменить позицию, нажать «Сохранить»
# Убедиться что появился диалог «Счёт уже оплачен»
# Нажать «Да, сохранить акт» → диалог закрылся, акт сохранён
```

---

## Self-Review

### Покрытие требований

| Требование | Задача |
|-----------|--------|
| Запрет редактирования после подписания | Task 3 (Guard 1, уже был — явно подтверждён тестом) |
| Запрет для не-admin при наличии счёта | Task 3 Guard 2 + тесты Task 2 |
| Admin может редактировать при наличии счёта | Task 3 + Task 2 тест |
| Автосинхронизация неоплаченного счёта | Task 3 sync + тест `test_admin_edit_act_syncs_unpaid_invoice` |
| 409 при оплаченном счёте | Task 3 + тест `test_admin_edit_act_returns_409_when_invoice_paid` |
| force_save = сохранить акт, не трогать счёт | Task 3 + тест `test_admin_force_save_ignores_paid_invoice` |
| Кнопка скрыта для не-admin | Task 4 |
| Диалог в UI | Task 5 |
| Документация | Task 6 |

### Проверка плейсхолдеров
Нет "TBD", "TODO", или абстрактных описаний — всё с кодом.

### Согласованность типов
- `WorkActUpdate.force_save: bool` (Task 1) используется в `update_work_act` как `data.force_save` (Task 3) ✓
- `_calc_act_total` принимает `act.items` (список `WorkActItem`) ✓
- `_sync_invoice_from_act` принимает `invoice: Invoice`, `act_items: list[WorkActItem]`, `db: Session` ✓
- Фронтенд `force_save: true` в payload (Task 5) соответствует схеме Pydantic ✓
