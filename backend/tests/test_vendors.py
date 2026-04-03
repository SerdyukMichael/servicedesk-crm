"""
Unit tests — /api/v1/vendors
"""
import pytest
from tests.conftest import make_admin, make_engineer, make_vendor, auth_headers


def _admin(db):
    u = make_admin(db)
    return auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db)
    return auth_headers(u.id, u.roles)


class TestVendors:
    def test_list_vendors_authenticated(self, client, db):
        make_vendor(db)
        res = client.get("/api/v1/vendors", headers=_eng(db))
        assert res.status_code == 200

    def test_unauthenticated_blocked(self, client, db):
        res = client.get("/api/v1/vendors")
        assert res.status_code == 401

    def test_admin_creates_vendor(self, client, db):
        res = client.post("/api/v1/vendors", headers=_admin(db), json={
            "name": "New Vendor",
            "contact_name": "John",
            "contact_email": "john@vendor.com",
        })
        assert res.status_code == 201
        assert res.json()["name"] == "New Vendor"

    def test_engineer_cannot_create_vendor(self, client, db):
        res = client.post("/api/v1/vendors", headers=_eng(db), json={"name": "X"})
        assert res.status_code == 403

    def test_get_vendor_by_id(self, client, db):
        v = make_vendor(db, name="NCR Russia")
        res = client.get(f"/api/v1/vendors/{v.id}", headers=_eng(db))
        assert res.status_code == 200
        assert res.json()["name"] == "NCR Russia"

    def test_get_nonexistent_vendor(self, client, db):
        res = client.get("/api/v1/vendors/999999", headers=_eng(db))
        assert res.status_code == 404

    def test_admin_updates_vendor(self, client, db):
        v = make_vendor(db)
        res = client.put(f"/api/v1/vendors/{v.id}", headers=_admin(db),
                         json={"name": "Updated Vendor"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Vendor"

    def test_admin_deletes_vendor(self, client, db):
        v = make_vendor(db)
        res = client.delete(f"/api/v1/vendors/{v.id}", headers=_admin(db))
        assert res.status_code == 204
