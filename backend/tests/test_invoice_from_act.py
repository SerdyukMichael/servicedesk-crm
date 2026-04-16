"""
Tests for POST /invoices/from-act/{ticket_id} — create invoice from work act.
"""
import pytest
from sqlalchemy import text
from tests.conftest import (
    make_admin, auth_headers, make_client,
    make_equipment_model, make_equipment, make_ticket,
    make_service_catalog_item, make_spare_part,
)


def _set_status(db, ticket_id, status):
    db.execute(text("UPDATE tickets SET status=:s WHERE id=:id"), {"s": status, "id": ticket_id})
    db.commit()


def _create_ticket_in_progress(db, admin):
    cli = make_client(db)
    model = make_equipment_model(db)
    equip = make_equipment(db, cli.id, model.id)
    ticket = make_ticket(db, cli.id, equip.id, admin.id)
    _set_status(db, ticket.id, "in_progress")
    return ticket, cli


def _post_act(client_fixture, ticket_id, headers, items, desc="Ремонт завершён"):
    return client_fixture.post(f"/api/v1/tickets/{ticket_id}/work-act", json={
        "work_description": desc,
        "items": items,
    }, headers=headers)


class TestInvoiceFromAct:
    def test_create_invoice_from_act(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        ticket, cli = _create_ticket_in_progress(db, admin)
        svc = make_service_catalog_item(db, code="SRV-INV-01", unit_price=1500.00)
        part = make_spare_part(db, sku="PART-INV-01", quantity=10)

        _post_act(client, ticket.id, headers, [
            {"item_type": "service", "service_id": svc.id, "name": "Диагностика",
             "quantity": "1", "unit": "шт", "unit_price": "1500.00"},
            {"item_type": "part", "part_id": part.id, "name": "Ролик",
             "quantity": "2", "unit": "шт", "unit_price": "500.00"},
        ])

        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["client_id"] == cli.id
        assert data["ticket_id"] == ticket.id
        assert data["status"] == "draft"
        assert len(data["items"]) == 2
        totals = {item["description"]: item["total"] for item in data["items"]}
        assert totals["Диагностика"] == "1500.00"
        assert totals["Ролик"] == "1000.00"

    def test_cannot_create_invoice_without_act(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        ticket, _ = _create_ticket_in_progress(db, admin)

        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 404

    def test_invoice_from_act_preserves_prices(self, client, db):
        """BR-P-003: изменение прайса не влияет на счёт из акта."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        ticket, _ = _create_ticket_in_progress(db, admin)
        svc = make_service_catalog_item(db, code="SRV-INV-02", unit_price=1500.00)

        _post_act(client, ticket.id, headers, [{
            "item_type": "service", "service_id": svc.id,
            "name": "Диагностика", "quantity": "1", "unit": "шт", "unit_price": "1500.00",
        }])

        # Меняем цену в прайсе
        client.patch(f"/api/v1/service-catalog/{svc.id}",
                     json={"unit_price": "9999.00"}, headers=headers)

        # Счёт из акта должен содержать старую цену (1500)
        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 201
        assert r.json()["items"][0]["unit_price"] == "1500.00"

    def test_invoice_from_act_no_items_creates_empty_invoice(self, client, db):
        """Акт без items — счёт создаётся, но пустой."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        ticket, cli = _create_ticket_in_progress(db, admin)

        _post_act(client, ticket.id, headers, [], desc="Только описание")

        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["items"] == []
        assert data["client_id"] == cli.id

    def test_invoice_from_nonexistent_ticket(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        r = client.post("/api/v1/invoices/from-act/99999", headers=headers)
        assert r.status_code == 404

    def test_invoice_totals_calculated_correctly(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        ticket, _ = _create_ticket_in_progress(db, admin)
        svc = make_service_catalog_item(db, code="SRV-INV-03", unit_price=2000.00)

        _post_act(client, ticket.id, headers, [{
            "item_type": "service", "service_id": svc.id,
            "name": "Ремонт", "quantity": "3", "unit": "шт", "unit_price": "2000.00",
        }])

        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 201
        data = r.json()
        # НДС "в т.ч.": total_amount = сумма позиций (цены уже с НДС); vat вычисляется из итога
        # 3 × 2000 = 6000; vat = 6000 / 122 * 22 ≈ 1081.97; subtotal = 6000 - 1081.97 = 4918.03
        from decimal import Decimal
        total = Decimal(data["total_amount"])
        vat = Decimal(data["vat_amount"])
        subtotal = Decimal(data["subtotal"])
        vat_rate = Decimal(data["vat_rate"])
        assert total == Decimal("6000.00")          # сумма позиций (не растёт)
        expected_vat = (total * vat_rate / (100 + vat_rate)).quantize(Decimal("0.01"))
        assert vat == expected_vat                  # НДС в т.ч.
        assert subtotal + vat == total              # subtotal + vat = total
