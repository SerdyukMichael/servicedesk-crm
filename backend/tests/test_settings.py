"""Tests for /api/v1/settings endpoints."""
import pytest
from app.models import SystemSetting
from tests.conftest import make_admin, make_engineer, auth_headers


def seed_currency(db, code="RUB", name="Российский рубль"):
    for key, value in [("currency_code", code), ("currency_name", name)]:
        db.add(SystemSetting(key=key, value=value))
    db.commit()


class TestGetCurrency:
    def test_returns_defaults(self, client, db):
        seed_currency(db)
        admin = make_admin(db)
        headers = auth_headers(admin.id, ["admin"])
        r = client.get("/api/v1/settings/currency", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["currency_code"] == "RUB"
        assert data["currency_name"] == "Российский рубль"

    def test_unauthenticated_blocked(self, client, db):
        seed_currency(db)
        r = client.get("/api/v1/settings/currency")
        assert r.status_code == 401

    def test_missing_setting_returns_404(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, ["admin"])
        r = client.get("/api/v1/settings/currency", headers=headers)
        assert r.status_code == 404


class TestUpdateCurrency:
    def test_admin_can_update(self, client, db):
        seed_currency(db)
        admin = make_admin(db)
        headers = auth_headers(admin.id, ["admin"])
        r = client.put(
            "/api/v1/settings/currency",
            json={"currency_code": "USD", "currency_name": "US Dollar"},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["currency_code"] == "USD"
        assert data["currency_name"] == "US Dollar"

    def test_db_updated_after_put(self, client, db):
        seed_currency(db)
        admin = make_admin(db)
        headers = auth_headers(admin.id, ["admin"])
        client.put(
            "/api/v1/settings/currency",
            json={"currency_code": "KZT", "currency_name": "Казахстанский тенге"},
            headers=headers,
        )
        row = db.get(SystemSetting, "currency_code")
        assert row.value == "KZT"

    def test_engineer_cannot_update(self, client, db):
        seed_currency(db)
        eng = make_engineer(db)
        headers = auth_headers(eng.id, ["engineer"])
        r = client.put(
            "/api/v1/settings/currency",
            json={"currency_code": "USD", "currency_name": "US Dollar"},
            headers=headers,
        )
        assert r.status_code == 403

    def test_invalid_code_rejected(self, client, db):
        seed_currency(db)
        admin = make_admin(db)
        headers = auth_headers(admin.id, ["admin"])
        r = client.put(
            "/api/v1/settings/currency",
            json={"currency_code": "us", "currency_name": "US Dollar"},
            headers=headers,
        )
        assert r.status_code == 422

    def test_empty_name_rejected(self, client, db):
        seed_currency(db)
        admin = make_admin(db)
        headers = auth_headers(admin.id, ["admin"])
        r = client.put(
            "/api/v1/settings/currency",
            json={"currency_code": "USD", "currency_name": ""},
            headers=headers,
        )
        assert r.status_code == 422

    def test_unauthenticated_cannot_update(self, client, db):
        seed_currency(db)
        r = client.put(
            "/api/v1/settings/currency",
            json={"currency_code": "USD", "currency_name": "US Dollar"},
        )
        assert r.status_code == 401
