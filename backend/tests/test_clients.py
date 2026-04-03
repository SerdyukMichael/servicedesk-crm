"""
Unit tests — /api/v1/clients
Covers: CRUD, soft-delete, search, RBAC, 404.
"""
import pytest
from tests.conftest import (
    make_admin, make_user, make_engineer, make_client,
    auth_headers,
)


def _admin_hdrs(db):
    u = make_admin(db)
    return auth_headers(u.id, u.roles)


def _sales_hdrs(db):
    u = make_user(db, email="sales@test.com", roles=["sales_mgr"])
    return auth_headers(u.id, u.roles)


def _eng_hdrs(db):
    u = make_engineer(db)
    return auth_headers(u.id, u.roles)


class TestListClients:
    def test_any_authenticated_can_list(self, client, db):
        make_client(db)
        res = client.get("/api/v1/clients", headers=_eng_hdrs(db))
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_unauthenticated_returns_401(self, client, db):
        res = client.get("/api/v1/clients")
        assert res.status_code == 401

    def test_pagination_returns_has_more(self, client, db):
        headers = _admin_hdrs(db)
        for i in range(5):
            make_client(db, name=f"Client {i}")
        res = client.get("/api/v1/clients", headers=headers, params={"size": 2})
        data = res.json()
        assert len(data["items"]) <= 2
        assert data["pages"] > 1

    def test_search_by_name(self, client, db):
        headers = _admin_hdrs(db)
        make_client(db, name="Сбербанк")
        make_client(db, name="ВТБ Банк")
        res = client.get("/api/v1/clients", headers=headers, params={"search": "Сбер"})
        assert res.status_code == 200
        items = res.json()["items"]
        assert all("Сбер" in c["name"] for c in items)

    def test_filter_by_contract_type(self, client, db):
        headers = _admin_hdrs(db)
        make_client(db, name="Premium Client", contract_type="premium")
        make_client(db, name="Standard Client", contract_type="standard")
        res = client.get("/api/v1/clients", headers=headers, params={"contract_type": "premium"})
        for c in res.json()["items"]:
            assert c["contract_type"] == "premium"


class TestCreateClient:
    # Minimal payload with all required fields
    _REQ = {"inn": "1234567890", "city": "Москва", "contract_type": "none", "contract_number": "ДГ-001"}

    def test_admin_creates_client(self, client, db):
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Новый Клиент", **self._REQ})
        assert res.status_code == 201
        assert res.json()["name"] == "Новый Клиент"

    def test_sales_mgr_creates_client(self, client, db):
        res = client.post("/api/v1/clients", headers=_sales_hdrs(db),
                          json={"name": "Sales Client", **self._REQ})
        assert res.status_code == 201

    def test_engineer_cannot_create_client(self, client, db):
        res = client.post("/api/v1/clients", headers=_eng_hdrs(db),
                          json={"name": "X", **self._REQ})
        assert res.status_code == 403

    def test_missing_name_returns_422(self, client, db):
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={**self._REQ})
        assert res.status_code == 422

    def test_missing_inn_returns_422(self, client, db):
        """ИНН обязателен — пропуск → 422."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test", "city": "Москва", "contract_type": "none", "contract_number": "ДГ-001"})
        assert res.status_code == 422

    def test_missing_city_returns_422(self, client, db):
        """Город обязателен — пропуск → 422."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test", "inn": "1234567890", "contract_type": "none", "contract_number": "ДГ-001"})
        assert res.status_code == 422

    def test_missing_contract_type_returns_422(self, client, db):
        """Тип договора обязателен — пропуск → 422."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test", "inn": "1234567890", "city": "Москва", "contract_number": "ДГ-001"})
        assert res.status_code == 422

    def test_missing_contract_number_returns_422(self, client, db):
        """Номер договора обязателен — пропуск → 422."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test", "inn": "1234567890", "city": "Москва", "contract_type": "none"})
        assert res.status_code == 422

    def test_empty_inn_returns_422(self, client, db):
        """Пустой ИНН → 422."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test", "inn": "", "city": "Москва", "contract_type": "none", "contract_number": "ДГ-001"})
        assert res.status_code == 422

    def test_empty_contract_type_returns_422(self, client, db):
        """Пустой contract_type → 422 (обязательное поле)."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test Default", "inn": "1234567890", "city": "Москва",
                                "contract_type": "", "contract_number": "ДГ-001"})
        assert res.status_code == 422

    def test_created_client_not_deleted(self, client, db):
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Test", **self._REQ})
        assert res.json()["is_deleted"] is False

    def test_create_with_frontend_contract_types(self, client, db):
        """Форматы contract_type из фронтенд-формы должны сохраняться (не блокироваться Enum)."""
        frontend_types = ["full_service", "partial", "time_and_material", "warranty"]
        hdrs = _admin_hdrs(db)
        for ct in frontend_types:
            res = client.post("/api/v1/clients", headers=hdrs,
                              json={"name": f"Bank {ct}", "inn": "1234567890",
                                    "city": "Москва", "contract_type": ct, "contract_number": "ДГ-001"})
            assert res.status_code == 201, f"contract_type='{ct}' вернул {res.status_code}: {res.text}"
            assert res.json()["contract_type"] == ct

    def test_create_with_city_field(self, client, db):
        """Поле city должно сохраняться и возвращаться в ответе."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Алматы Банк", "contract_type": "full_service",
                                "city": "Алматы", "inn": "123456789012", "contract_number": "ДГ-001"})
        assert res.status_code == 201
        data = res.json()
        assert data["city"] == "Алматы"
        assert data["inn"] == "123456789012"

    def test_create_cyrillic_name(self, client, db):
        """Кирилличный name должен сохраняться корректно."""
        res = client.post("/api/v1/clients", headers=_admin_hdrs(db),
                          json={"name": "Банк Центркредит", **self._REQ})
        assert res.status_code == 201
        assert res.json()["name"] == "Банк Центркредит"


class TestGetClient:
    def test_get_existing_client(self, client, db):
        c = make_client(db, name="Альфа-Банк")
        res = client.get(f"/api/v1/clients/{c.id}", headers=_eng_hdrs(db))
        assert res.status_code == 200
        assert res.json()["name"] == "Альфа-Банк"

    def test_get_nonexistent_returns_404(self, client, db):
        res = client.get("/api/v1/clients/999999", headers=_eng_hdrs(db))
        assert res.status_code == 404
        assert res.json()["error"] == "NOT_FOUND"

    def test_get_deleted_client_returns_404(self, client, db):
        c = make_client(db)
        c.is_deleted = True
        db.commit()
        res = client.get(f"/api/v1/clients/{c.id}", headers=_eng_hdrs(db))
        assert res.status_code == 404


def _svc_hdrs(db):
    u = make_user(db, email="svc@test.com", roles=["svc_mgr"])
    return auth_headers(u.id, u.roles)


class TestUpdateClient:
    def test_admin_can_update(self, client, db):
        c = make_client(db, name="Before")
        res = client.put(f"/api/v1/clients/{c.id}", headers=_admin_hdrs(db),
                         json={"name": "After"})
        assert res.status_code == 200
        assert res.json()["name"] == "After"

    def test_sales_mgr_can_update(self, client, db):
        c = make_client(db, name="Old Name")
        res = client.put(f"/api/v1/clients/{c.id}", headers=_sales_hdrs(db),
                         json={"name": "New Name"})
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

    def test_svc_mgr_can_update(self, client, db):
        """svc_mgr тоже должен иметь право редактировать клиента."""
        c = make_client(db, name="Old")
        res = client.put(f"/api/v1/clients/{c.id}", headers=_svc_hdrs(db),
                         json={"name": "Updated by SvcMgr"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated by SvcMgr"

    def test_engineer_cannot_update(self, client, db):
        c = make_client(db)
        res = client.put(f"/api/v1/clients/{c.id}", headers=_eng_hdrs(db),
                         json={"name": "Hacked"})
        assert res.status_code == 403

    def test_update_contract_type_frontend_values(self, client, db):
        """Все типы договора из формы фронтенда должны сохраняться при обновлении."""
        hdrs = _admin_hdrs(db)
        c = make_client(db, name="Test")
        for ct in ["full_service", "partial", "time_and_material", "warranty"]:
            res = client.put(f"/api/v1/clients/{c.id}", headers=hdrs,
                             json={"contract_type": ct})
            assert res.status_code == 200, f"contract_type='{ct}' вернул {res.status_code}"
            assert res.json()["contract_type"] == ct

    def test_update_city_field(self, client, db):
        """Поле city должно обновляться."""
        c = make_client(db, name="Bank")
        res = client.put(f"/api/v1/clients/{c.id}", headers=_admin_hdrs(db),
                         json={"city": "Астана"})
        assert res.status_code == 200
        assert res.json()["city"] == "Астана"

    def test_update_partial_fields_preserved(self, client, db):
        """Частичное обновление — незатронутые поля остаются прежними."""
        hdrs = _admin_hdrs(db)
        c = make_client(db, name="Preserved Bank")
        # Сначала ставим inn
        client.put(f"/api/v1/clients/{c.id}", headers=hdrs, json={"inn": "9876543210"})
        # Потом обновляем только name — inn должен остаться
        res = client.put(f"/api/v1/clients/{c.id}", headers=hdrs,
                         json={"name": "New Preserved Bank"})
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "New Preserved Bank"
        assert data["inn"] == "9876543210"

    def test_update_nonexistent_returns_404(self, client, db):
        res = client.put("/api/v1/clients/999999", headers=_admin_hdrs(db),
                         json={"name": "Ghost"})
        assert res.status_code == 404


class TestDeleteClient:
    def test_admin_soft_deletes_client(self, client, db):
        from app.models import Client as ClientModel
        c = make_client(db)
        res = client.delete(f"/api/v1/clients/{c.id}", headers=_admin_hdrs(db))
        assert res.status_code == 204
        db_client = db.query(ClientModel).filter_by(id=c.id).first()
        assert db_client.is_deleted is True

    def test_engineer_cannot_delete(self, client, db):
        c = make_client(db)
        res = client.delete(f"/api/v1/clients/{c.id}", headers=_eng_hdrs(db))
        assert res.status_code == 403

    def test_deleted_client_not_in_list(self, client, db):
        headers = _admin_hdrs(db)
        c = make_client(db, name="ToDelete")
        client.delete(f"/api/v1/clients/{c.id}", headers=headers)
        res = client.get("/api/v1/clients", headers=headers)
        names = [x["name"] for x in res.json()["items"]]
        assert "ToDelete" not in names
