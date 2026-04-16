"""
Tests for work act edit lock when invoice exists (BR-F-126, BR-F-127).

Covered:
- non-admin (engineer, svc_mgr) cannot edit act if invoice exists for ticket → 403
- admin CAN edit act even if invoice exists
- admin edit act with unpaid invoice → invoice items replaced + totals recalculated → 200
- admin edit act with paid invoice, no force_save → 409 INVOICE_PAID_MISMATCH
- admin edit act with paid invoice, force_save=True → act saved, invoice untouched → 200
- admin edit act when no invoice → just saves, 200
- engineer can edit act when no invoice → 200
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from tests.conftest import (
    make_admin, make_svc_mgr, make_engineer, make_client,
    make_equipment_model, make_equipment, auth_headers,
)
from app.models import Invoice, InvoiceItem


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
        cl, eq, eng, admin,
    )


def _create_ticket_with_act(http, admin_hdrs, eng, cl, eq):
    """Create ticket, assign to engineer, move to in_progress, create work act (1 item, 100.00)."""
    r = http.post("/api/v1/tickets", headers=admin_hdrs, json={
        "client_id": cl.id, "equipment_id": eq.id,
        "title": "Lock test", "type": "repair", "priority": "medium",
    })
    assert r.status_code == 201, r.text
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
    assert r.status_code == 201, r.text
    return tid


def _create_invoice_for_ticket(db, ticket_id, client_id, creator_id, paid=False):
    """Directly insert invoice + 1 item into DB."""
    inv = Invoice(
        number=f"TEST-INV-{ticket_id}-{'paid' if paid else 'draft'}",
        client_id=client_id,
        ticket_id=ticket_id,
        type="service",
        status="paid" if paid else "draft",
        issue_date=date.today(),
        # НДС "в т.ч." 22%: total=122, vat=122/122*22=22, subtotal=100
        subtotal=Decimal("100.00"),
        vat_rate=Decimal("22.00"),
        vat_amount=Decimal("22.00"),
        total_amount=Decimal("122.00"),
        created_by=creator_id,
        paid_at=datetime.utcnow() if paid else None,
    )
    db.add(inv)
    db.flush()
    db.add(InvoiceItem(
        invoice_id=inv.id,
        description="Диагностика",
        quantity=Decimal("1"),
        unit="шт",
        unit_price=Decimal("100.00"),
        total=Decimal("100.00"),
        sort_order=0,
    ))
    db.commit()
    db.refresh(inv)
    return inv


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def setup(client, db):
    admin_hdrs, svc_hdrs, eng_hdrs, cl, eq, eng, admin_user = _setup(db)
    return {
        "http": client,
        "admin": admin_hdrs,
        "svc": svc_hdrs,
        "eng": eng_hdrs,
        "cl": cl,
        "eq": eq,
        "eng_obj": eng,
        "admin_user": admin_user,
    }


# ─── no invoice: anyone with role can edit ────────────────────────────────────

class TestActEditNoInvoice:
    def test_admin_can_edit_act_without_invoice(self, setup):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"work_description": "Обновлено"})
        assert r.status_code == 200

    def test_engineer_can_edit_act_without_invoice(self, setup):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["eng"],
                            json={"work_description": "Обновлено инженером"})
        assert r.status_code == 200


# ─── invoice exists: only admin can edit ──────────────────────────────────────

class TestActLockWithInvoice:
    def test_engineer_cannot_edit_act_when_invoice_exists(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["eng"],
                            json={"work_description": "Попытка инженера"})
        assert r.status_code == 403
        assert r.json()["error"] == "ACT_LOCKED_INVOICE_EXISTS"

    def test_svc_mgr_cannot_edit_act_when_invoice_exists(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["svc"],
                            json={"work_description": "Попытка svc_mgr"})
        assert r.status_code == 403
        assert r.json()["error"] == "ACT_LOCKED_INVOICE_EXISTS"

    def test_admin_can_edit_act_when_invoice_exists(self, setup, db):
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"work_description": "Обновлено администратором",
                                  "items": [{"item_type": "service", "name": "Замена",
                                             "quantity": "2", "unit": "шт",
                                             "unit_price": "200.00", "sort_order": 0}]})
        assert r.status_code == 200


# ─── unpaid invoice: auto-sync ────────────────────────────────────────────────

class TestActSyncUnpaidInvoice:
    def test_admin_edit_act_syncs_unpaid_invoice(self, setup, db):
        """After admin edits act items, unpaid invoice is replaced and totals recalculated."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
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
        # НДС "в т.ч.": total_amount = сумма позиций, vat = total / 122 * 22 (ставка 22%)
        assert inv.total_amount == Decimal("500.00")
        expected_vat = (Decimal("500.00") * inv.vat_rate / (100 + inv.vat_rate)).quantize(Decimal("0.01"))
        assert inv.vat_amount == expected_vat
        assert inv.subtotal == inv.total_amount - inv.vat_amount
        assert len(inv.items) == 1
        assert inv.items[0].description == "Замена платы"


# ─── paid invoice: mismatch dialog ───────────────────────────────────────────

class TestActPaidInvoiceMismatch:
    def test_admin_edit_returns_409_when_invoice_paid(self, setup, db):
        """When invoice is paid and totals differ, return 409 INVOICE_PAID_MISMATCH."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
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
        """With force_save=True, act is saved but paid invoice is NOT modified."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        inv = _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=True)
        original_total = inv.total_amount  # 122.00

        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"force_save": True,
                                  "items": [
                                      {"item_type": "service", "name": "Новая работа",
                                       "quantity": "1", "unit": "шт",
                                       "unit_price": "999.00", "sort_order": 0},
                                  ]})
        assert r.status_code == 200
        assert r.json()["items"][0]["unit_price"] == "999.00"

        db.refresh(inv)
        assert inv.total_amount == original_total  # счёт не тронут

    def test_paid_invoice_detected_even_if_newer_draft_exists(self, setup, db):
        """If ticket has both a paid invoice (older) and a draft invoice (newer),
        editing act with changed total must still return 409 (not silently succeed)."""
        s = setup
        tid = _create_ticket_with_act(s["http"], s["admin"], s["eng_obj"], s["cl"], s["eq"])
        # Создаём оплаченный счёт (старый)
        paid_inv = _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=True)
        # Создаём черновой счёт (новый — он попал бы на первое место при ORDER BY created_at DESC)
        _create_invoice_for_ticket(db, tid, s["cl"].id, s["admin_user"].id, paid=False)

        # Меняем позиции акта — итог изменится (100 → 999)
        r = s["http"].patch(f"/api/v1/tickets/{tid}/work-act",
                            headers=s["admin"],
                            json={"items": [
                                {"item_type": "service", "name": "Новая работа",
                                 "quantity": "1", "unit": "шт",
                                 "unit_price": "999.00", "sort_order": 0},
                            ]})
        # Должен вернуть 409, а не 200
        assert r.status_code == 409
        body = r.json()
        assert body["error"] == "INVOICE_PAID_MISMATCH"

        # Оплаченный счёт не должен измениться
        db.refresh(paid_inv)
        assert paid_inv.total_amount == Decimal("122.00")
