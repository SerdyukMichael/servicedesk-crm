"""
Tests for WorkActItem — structured items in work acts (services + parts with prices).
"""
import pytest
from decimal import Decimal
from sqlalchemy import text
from tests.conftest import (
    make_admin, make_engineer, admin_headers, auth_headers,
    make_client, make_equipment_model, make_equipment, make_ticket,
    make_spare_part, make_service_catalog_item,
)


def _set_ticket_status(db, ticket_id, status):
    db.execute(text("UPDATE tickets SET status=:s WHERE id=:id"), {"s": status, "id": ticket_id})
    db.commit()


def _make_ticket_in_progress(db, cli, admin):
    model = make_equipment_model(db)
    equip = make_equipment(db, cli.id, model.id)
    ticket = make_ticket(db, cli.id, equip.id, admin.id)
    _set_ticket_status(db, ticket.id, "in_progress")
    return ticket


class TestWorkActItems:
    def test_create_act_with_service_item(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="SRV-001", unit_price=1500.00)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Диагностика проведена",
            "items": [
                {
                    "item_type": "service",
                    "service_id": svc.id,
                    "name": "Диагностика банкомата",
                    "quantity": "1",
                    "unit": "шт",
                    "unit_price": "1500.00",
                }
            ]
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["item_type"] == "service"
        assert data["items"][0]["total"] == "1500.00"

    def test_create_act_with_part_item(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        part = make_spare_part(db, sku="PART-001", quantity=5)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Замена ролика",
            "items": [
                {
                    "item_type": "part",
                    "part_id": part.id,
                    "name": "Ролик подачи",
                    "quantity": "2",
                    "unit": "шт",
                    "unit_price": "500.00",
                }
            ]
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["total"] == "1000.00"

    def test_create_act_with_mixed_items(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="SRV-002", unit_price=2000.00)
        part = make_spare_part(db, sku="PART-002", quantity=10)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Полный ремонт",
            "items": [
                {
                    "item_type": "service",
                    "service_id": svc.id,
                    "name": "Ремонт",
                    "quantity": "1",
                    "unit": "шт",
                    "unit_price": "2000.00",
                },
                {
                    "item_type": "part",
                    "part_id": part.id,
                    "name": "Картридж",
                    "quantity": "3",
                    "unit": "шт",
                    "unit_price": "300.00",
                }
            ]
        }, headers=headers)
        assert r.status_code == 201
        assert len(r.json()["items"]) == 2

    def test_get_act_returns_items(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="SRV-003", unit_price=500.00)

        client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Test",
            "items": [{
                "item_type": "service",
                "service_id": svc.id,
                "name": "Выезд",
                "quantity": "1",
                "unit": "шт",
                "unit_price": "500.00",
            }]
        }, headers=headers)

        r = client.get(f"/api/v1/tickets/{ticket.id}/work-act", headers=headers)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_act_without_items_still_works(self, client, db):
        """Backward compatibility: акт можно сохранить без items."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Только описание, без позиций",
        }, headers=headers)
        assert r.status_code == 201
        assert r.json()["items"] == []
