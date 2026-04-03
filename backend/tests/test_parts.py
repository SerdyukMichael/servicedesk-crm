"""
Unit tests — /api/v1/parts
Covers: CRUD, количество, low_stock фильтр, корректировка остатка, RBAC.
"""
import pytest
from tests.conftest import (
    make_admin, make_engineer, make_user,
    make_spare_part, make_vendor,
    auth_headers,
)


def _admin(db):
    u = make_admin(db)
    return auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db)
    return auth_headers(u.id, u.roles)


def _warehouse(db):
    u = make_user(db, email="wh@t.com", roles=["warehouse"])
    return auth_headers(u.id, u.roles)


class TestListParts:
    def test_all_authenticated_can_list(self, client, db):
        make_spare_part(db)
        res = client.get("/api/v1/parts", headers=_eng(db))
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_unauthenticated_blocked(self, client, db):
        res = client.get("/api/v1/parts")
        assert res.status_code == 401

    def test_low_stock_filter(self, client, db):
        headers = _admin(db)
        make_spare_part(db, sku="LOW-001", quantity=1, min_quantity=5)
        make_spare_part(db, sku="OK-001", quantity=10, min_quantity=2)
        res = client.get("/api/v1/parts", headers=headers, params={"low_stock": True})
        assert res.status_code == 200
        for part in res.json()["items"]:
            assert part["quantity"] < part["min_quantity"]

    def test_filter_by_category(self, client, db):
        headers = _admin(db)
        p = make_spare_part(db, sku="CAT-001")
        res = client.get("/api/v1/parts", headers=headers, params={"category": p.category})
        for part in res.json()["items"]:
            assert part["category"] == p.category


class TestCreatePart:
    def test_admin_creates_part(self, client, db):
        res = client.post("/api/v1/parts", headers=_admin(db), json={
            "sku": "NEW-SKU-001",
            "name": "Test Part",
            "category": "consumable",
            "unit": "шт",
            "quantity": 5,
            "min_quantity": 2,
            "unit_price": "150.00",
            "currency": "RUB",
        })
        assert res.status_code == 201
        assert res.json()["sku"] == "NEW-SKU-001"

    def test_warehouse_creates_part(self, client, db):
        res = client.post("/api/v1/parts", headers=_warehouse(db), json={
            "sku": "WH-SKU-001",
            "name": "WH Part",
            "category": "consumable",
            "unit": "шт",
            "quantity": 3,
            "min_quantity": 1,
            "unit_price": "75.00",
            "currency": "RUB",
        })
        assert res.status_code == 201

    def test_engineer_cannot_create(self, client, db):
        res = client.post("/api/v1/parts", headers=_eng(db), json={
            "sku": "ENG-001", "name": "X", "category": "consumable",
            "unit": "шт", "quantity": 1, "min_quantity": 0, "unit_price": "10.00", "currency": "RUB",
        })
        assert res.status_code == 403

    def test_duplicate_sku_returns_409(self, client, db):
        make_spare_part(db, sku="DUP-SKU")
        res = client.post("/api/v1/parts", headers=_admin(db), json={
            "sku": "DUP-SKU", "name": "Dup", "category": "consumable",
            "unit": "шт", "quantity": 1, "min_quantity": 0, "unit_price": "10.00", "currency": "RUB",
        })
        assert res.status_code == 409


class TestGetPart:
    def test_get_existing(self, client, db):
        p = make_spare_part(db, sku="GET-001")
        res = client.get(f"/api/v1/parts/{p.id}", headers=_eng(db))
        assert res.status_code == 200
        assert res.json()["sku"] == "GET-001"

    def test_get_nonexistent_returns_404(self, client, db):
        res = client.get("/api/v1/parts/999999", headers=_eng(db))
        assert res.status_code == 404


class TestUpdatePart:
    def test_admin_updates(self, client, db):
        p = make_spare_part(db)
        res = client.put(f"/api/v1/parts/{p.id}", headers=_admin(db),
                         json={"quantity": 99})
        assert res.status_code == 200
        assert res.json()["quantity"] == 99

    def test_engineer_cannot_update(self, client, db):
        p = make_spare_part(db)
        res = client.put(f"/api/v1/parts/{p.id}", headers=_eng(db),
                         json={"quantity": 0})
        assert res.status_code == 403


class TestAdjustStock:
    def test_positive_adjustment(self, client, db):
        p = make_spare_part(db, quantity=10)
        res = client.post(f"/api/v1/parts/{p.id}/adjust", headers=_warehouse(db),
                          json={"delta": 5, "reason": "Приход от поставщика"})
        assert res.status_code == 200
        assert res.json()["quantity"] == 15

    def test_negative_adjustment(self, client, db):
        p = make_spare_part(db, quantity=10)
        res = client.post(f"/api/v1/parts/{p.id}/adjust", headers=_warehouse(db),
                          json={"delta": -3, "reason": "Списание"})
        assert res.status_code == 200
        assert res.json()["quantity"] == 7

    def test_adjustment_below_zero_rejected(self, client, db):
        """Количество не может стать отрицательным."""
        p = make_spare_part(db, quantity=2)
        res = client.post(f"/api/v1/parts/{p.id}/adjust", headers=_warehouse(db),
                          json={"delta": -5, "reason": "Overuse"})
        assert res.status_code == 400

    def test_engineer_cannot_adjust(self, client, db):
        p = make_spare_part(db, quantity=10)
        res = client.post(f"/api/v1/parts/{p.id}/adjust", headers=_eng(db),
                          json={"delta": 1, "reason": "Test"})
        assert res.status_code == 403
