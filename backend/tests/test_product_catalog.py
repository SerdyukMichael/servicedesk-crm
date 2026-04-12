"""
Tests for ProductCatalog (price list for products/spare parts).
BR-F-121 / UC-102
"""
import pytest
from decimal import Decimal
from app.models import ProductCatalog
from app.schemas import ProductCatalogCreate

from tests.conftest import (
    make_admin, make_engineer, admin_headers, auth_headers,
    make_product_catalog_item,
)


# ── Model tests ───────────────────────────────────────────────────────────────

def test_product_catalog_model_created(db):
    item = ProductCatalog(
        code="PROD-001",
        name="Картридж ATM",
        category="spare_part",
        unit="pcs",
        unit_price=2500.00,
        currency="RUB",
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    assert item.id is not None
    assert item.code == "PROD-001"
    assert item.is_active is True


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_product_catalog_schema_valid():
    data = ProductCatalogCreate(
        code="PROD-001",
        name="Картридж ATM",
        category="spare_part",
        unit="pcs",
        unit_price=Decimal("2500.00"),
    )
    assert data.code == "PROD-001"
    assert data.currency == "RUB"   # default


def test_product_catalog_schema_requires_name():
    with pytest.raises(Exception):
        ProductCatalogCreate(code="PROD-001", category="other", unit="pcs", unit_price=0)


# ── CRUD API tests ────────────────────────────────────────────────────────────

class TestProductCatalogCRUD:

    def test_list_empty(self, client, db):
        headers = admin_headers(db)
        r = client.get("/api/v1/product-catalog", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["total"] == 0

    def test_create_item(self, client, db):
        headers = admin_headers(db)
        r = client.post("/api/v1/product-catalog", json={
            "code": "PROD-001",
            "name": "Картридж банкомата",
            "category": "spare_part",
            "unit": "pcs",
            "unit_price": "2500.00",
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "PROD-001"
        assert data["unit_price"] == "2500.00"
        assert data["is_active"] is True

    def test_create_duplicate_code_fails(self, client, db):
        headers = admin_headers(db)
        make_product_catalog_item(db, code="PROD-DUP")
        r = client.post("/api/v1/product-catalog", json={
            "code": "PROD-DUP",
            "name": "Другой",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 409

    def test_get_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-GET")
        r = client.get(f"/api/v1/product-catalog/{item.id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["code"] == "PROD-GET"

    def test_update_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-UPD", name="Старое имя")
        r = client.patch(f"/api/v1/product-catalog/{item.id}", json={
            "unit_price": "3000.00",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["unit_price"] == "3000.00"

    def test_deactivate_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-DEACT")
        r = client.patch(f"/api/v1/product-catalog/{item.id}", json={"is_active": False}, headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_deactivated_hidden_in_list_by_default(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-HIDDEN")
        client.patch(f"/api/v1/product-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/product-catalog", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id not in ids

    def test_show_inactive_with_param(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-SHOW")
        client.patch(f"/api/v1/product-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/product-catalog?include_inactive=true", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id in ids

    def test_filter_by_category(self, client, db):
        headers = admin_headers(db)
        make_product_catalog_item(db, code="PROD-SPARE", category="spare_part")
        make_product_catalog_item(db, code="PROD-OTHER", category="other")
        r = client.get("/api/v1/product-catalog?category=spare_part", headers=headers)
        items = r.json()["items"]
        assert all(i["category"] == "spare_part" for i in items)

    def test_engineer_cannot_create(self, client, db):
        eng = make_engineer(db)
        headers = auth_headers(eng.id, eng.roles)
        r = client.post("/api/v1/product-catalog", json={
            "code": "PROD-X",
            "name": "Test",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 403

    def test_delete_unused_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-DEL")
        r = client.delete(f"/api/v1/product-catalog/{item.id}", headers=headers)
        assert r.status_code == 204

    def test_delete_used_item_blocked(self, client, db):
        """BR-P-006: нельзя удалить если используется в работах."""
        from app.models import WorkActItem, WorkAct
        from tests.conftest import make_client, make_equipment_model, make_equipment, make_ticket

        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        prod = make_product_catalog_item(db, code="PROD-USED")
        cli = make_client(db)
        model = make_equipment_model(db)
        equip = make_equipment(db, cli.id, model.id)
        ticket = make_ticket(db, cli.id, equip.id, admin.id)

        act = WorkAct(ticket_id=ticket.id, engineer_id=admin.id)
        db.add(act)
        db.flush()
        act_item = WorkActItem(
            work_act_id=act.id,
            item_type="product",
            product_id=prod.id,
            name=prod.name,
            quantity=Decimal("1"),
            unit="pcs",
            unit_price=Decimal("500"),
            total=Decimal("500"),
        )
        db.add(act_item)
        db.commit()

        r = client.delete(f"/api/v1/product-catalog/{prod.id}", headers=headers)
        assert r.status_code == 409

    def test_unauthenticated_returns_401(self, client):
        r = client.get("/api/v1/product-catalog")
        assert r.status_code == 401
