"""
Tests for ServiceCatalog (price list for services/works).
"""
import pytest
from decimal import Decimal
from app.models import ServiceCatalog
from app.schemas import ServiceCatalogCreate, ServiceCatalogResponse


# ── Model tests ───────────────────────────────────────────────────────────────

def test_service_catalog_model_created(db):
    item = ServiceCatalog(
        code="SRV-001",
        name="Диагностика",
        category="diagnostics",
        unit="pcs",
        unit_price=1500.00,
        currency="RUB",
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    assert item.id is not None
    assert item.code == "SRV-001"
    assert item.is_active is True


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_service_catalog_schema_valid():
    data = ServiceCatalogCreate(
        code="SRV-001",
        name="Диагностика",
        category="diagnostics",
        unit="pcs",
        unit_price=Decimal("1500.00"),
    )
    assert data.code == "SRV-001"
    assert data.currency == "RUB"  # default


def test_service_catalog_schema_requires_name():
    with pytest.raises(Exception):
        ServiceCatalogCreate(code="SRV-001", category="other", unit="pcs", unit_price=0)


# ── CRUD API tests ────────────────────────────────────────────────────────────

from tests.conftest import (
    make_admin, make_engineer, admin_headers, auth_headers,
    make_service_catalog_item,
)


class TestServiceCatalogCRUD:
    def test_list_empty(self, client, db):
        headers = admin_headers(db)
        r = client.get("/api/v1/service-catalog", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_item(self, client, db):
        headers = admin_headers(db)
        r = client.post("/api/v1/service-catalog", json={
            "code": "SRV-001",
            "name": "Диагностика банкомата",
            "category": "diagnostics",
            "unit": "pcs",
            "unit_price": "1500.00",
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "SRV-001"
        assert data["unit_price"] == "1500.00"
        assert data["is_active"] is True

    def test_create_duplicate_code_fails(self, client, db):
        headers = admin_headers(db)
        make_service_catalog_item(db, code="SRV-001")
        r = client.post("/api/v1/service-catalog", json={
            "code": "SRV-001",
            "name": "Другое",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 409

    def test_update_item(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-002", name="Выезд")
        r = client.patch(f"/api/v1/service-catalog/{item.id}", json={
            "unit_price": "2000.00",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["unit_price"] == "2000.00"

    def test_deactivate_item(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-003")
        r = client.patch(f"/api/v1/service-catalog/{item.id}", json={"is_active": False}, headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_deactivated_hidden_in_list_by_default(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-004")
        client.patch(f"/api/v1/service-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/service-catalog", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id not in ids

    def test_show_inactive_with_param(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-005")
        client.patch(f"/api/v1/service-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/service-catalog?include_inactive=true", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id in ids

    def test_engineer_cannot_create(self, client, db):
        eng = make_engineer(db)
        headers = auth_headers(eng.id, eng.roles)
        r = client.post("/api/v1/service-catalog", json={
            "code": "SRV-X",
            "name": "Test",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 403

    def test_delete_unused_item(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-DEL")
        r = client.delete(f"/api/v1/service-catalog/{item.id}", headers=headers)
        assert r.status_code == 204

    def test_delete_used_item_blocked(self, client, db):
        """BR-P-006: нельзя удалить позицию, если она используется в документах."""
        from app.models import WorkActItem, WorkAct, Ticket, Client as ClientModel
        from tests.conftest import make_client, make_equipment_model, make_equipment, make_ticket

        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        svc = make_service_catalog_item(db, code="SRV-USED")
        cli = make_client(db)
        model = make_equipment_model(db)
        equip = make_equipment(db, cli.id, model.id)
        ticket = make_ticket(db, cli.id, equip.id, admin.id)

        act = WorkAct(ticket_id=ticket.id, engineer_id=admin.id)
        db.add(act)
        db.flush()
        act_item = WorkActItem(
            work_act_id=act.id,
            item_type="service",
            service_id=svc.id,
            name="Диагностика",
            quantity=Decimal("1"),
            unit="шт",
            unit_price=Decimal("1500"),
            total=Decimal("1500"),
        )
        db.add(act_item)
        db.commit()

        r = client.delete(f"/api/v1/service-catalog/{svc.id}", headers=headers)
        assert r.status_code == 409
