"""
Unit tests — /api/v1/equipment
Covers: CRUD, дубликат serial, soft-delete, гарантия, RBAC, история.
"""
import pytest
from tests.conftest import (
    make_admin, make_engineer, make_user,
    make_client, make_equipment_model, make_equipment,
    auth_headers,
)


def _admin(db):
    u = make_admin(db)
    return u, auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db)
    return u, auth_headers(u.id, u.roles)


def _svc(db):
    u = make_user(db, email="svc@t.com", roles=["svc_mgr"])
    return u, auth_headers(u.id, u.roles)


class TestEquipmentModels:
    def test_list_models(self, client, db):
        _, eng_hdrs = _eng(db)
        make_equipment_model(db, "NCR 6683")
        res = client.get("/api/v1/equipment/models", headers=eng_hdrs)
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert len(res.json()) >= 1

    def test_list_models_hides_inactive_by_default(self, client, db):
        _, eng_hdrs = _eng(db)
        m = make_equipment_model(db, "Inactive Model")
        m.is_active = False
        db.commit()
        res = client.get("/api/v1/equipment/models", headers=eng_hdrs)
        names = [item["name"] for item in res.json()]
        assert "Inactive Model" not in names

    def test_list_models_include_inactive(self, client, db):
        _, admin_hdrs = _admin(db)
        m = make_equipment_model(db, "Hidden Model")
        m.is_active = False
        db.commit()
        res = client.get("/api/v1/equipment/models?include_inactive=true", headers=admin_hdrs)
        names = [item["name"] for item in res.json()]
        assert "Hidden Model" in names

    def test_create_model_by_admin(self, client, db):
        _, admin_hdrs = _admin(db)
        res = client.post("/api/v1/equipment/models", headers=admin_hdrs, json={
            "name": "NCR 6622", "manufacturer": "NCR", "category": "atm",
            "warranty_months_default": 12,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "NCR 6622"
        assert data["category"] == "atm"
        assert data["warranty_months_default"] == 12
        assert data["is_active"] is True

    def test_create_model_by_svc_mgr(self, client, db):
        _, svc_hdrs = _svc(db)
        res = client.post("/api/v1/equipment/models", headers=svc_hdrs, json={
            "name": "Ingenico iPP320", "category": "pos_terminal",
        })
        assert res.status_code == 201

    def test_create_model_engineer_forbidden(self, client, db):
        _, eng_hdrs = _eng(db)
        res = client.post("/api/v1/equipment/models", headers=eng_hdrs, json={
            "name": "Some Model", "category": "atm",
        })
        assert res.status_code == 403

    def test_create_model_duplicate_name_returns_409(self, client, db):
        _, admin_hdrs = _admin(db)
        make_equipment_model(db, "NCR Duplicate")
        res = client.post("/api/v1/equipment/models", headers=admin_hdrs, json={
            "name": "NCR Duplicate", "category": "atm",
        })
        assert res.status_code == 409
        assert res.json()["error"] == "DUPLICATE_NAME"

    def test_update_model(self, client, db):
        _, admin_hdrs = _admin(db)
        m = make_equipment_model(db, "Old Name")
        res = client.put(f"/api/v1/equipment/models/{m.id}", headers=admin_hdrs, json={
            "name": "New Name", "warranty_months_default": 24,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "New Name"
        assert data["warranty_months_default"] == 24

    def test_update_model_not_found(self, client, db):
        _, admin_hdrs = _admin(db)
        res = client.put("/api/v1/equipment/models/999999", headers=admin_hdrs, json={"name": "X"})
        assert res.status_code == 404

    def test_update_model_duplicate_name_409(self, client, db):
        _, admin_hdrs = _admin(db)
        make_equipment_model(db, "Existing Model")
        m2 = make_equipment_model(db, "Other Model")
        res = client.put(f"/api/v1/equipment/models/{m2.id}", headers=admin_hdrs, json={
            "name": "Existing Model",
        })
        assert res.status_code == 409

    def test_deactivate_model(self, client, db):
        _, admin_hdrs = _admin(db)
        m = make_equipment_model(db, "To Deactivate")
        res = client.patch(f"/api/v1/equipment/models/{m.id}/deactivate", headers=admin_hdrs)
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    def test_activate_model(self, client, db):
        _, admin_hdrs = _admin(db)
        m = make_equipment_model(db, "To Activate")
        m.is_active = False
        db.commit()
        res = client.patch(f"/api/v1/equipment/models/{m.id}/activate", headers=admin_hdrs)
        assert res.status_code == 200
        assert res.json()["is_active"] is True

    def test_deactivate_not_found(self, client, db):
        _, admin_hdrs = _admin(db)
        res = client.patch("/api/v1/equipment/models/999999/deactivate", headers=admin_hdrs)
        assert res.status_code == 404

    def test_response_includes_warranty_months(self, client, db):
        _, eng_hdrs = _eng(db)
        m = make_equipment_model(db, "Warranty Model")
        m.warranty_months_default = 36
        db.commit()
        res = client.get("/api/v1/equipment/models", headers=eng_hdrs)
        found = next((item for item in res.json() if item["name"] == "Warranty Model"), None)
        assert found is not None
        assert found["warranty_months_default"] == 36


class TestCreateEquipment:
    def test_admin_creates_equipment(self, client, db):
        _, admin_hdrs = _admin(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        res = client.post("/api/v1/equipment", headers=admin_hdrs, json={
            "client_id": cl.id,
            "model_id": model.id,
            "serial_number": "SN-UNIQUE-001",
            "location": "Test Office",
        })
        assert res.status_code == 201
        assert res.json()["serial_number"] == "SN-UNIQUE-001"

    def test_duplicate_serial_returns_409(self, client, db):
        _, admin_hdrs = _admin(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        payload = {"client_id": cl.id, "model_id": model.id,
                   "serial_number": "DUP-001", "location": "A"}
        client.post("/api/v1/equipment", headers=admin_hdrs, json=payload)
        res = client.post("/api/v1/equipment", headers=admin_hdrs, json=payload)
        assert res.status_code == 409
        assert res.json()["error"] in ("CONFLICT", "DUPLICATE_SERIAL")

    def test_engineer_cannot_create(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        res = client.post("/api/v1/equipment", headers=eng_hdrs, json={
            "client_id": cl.id, "model_id": model.id,
            "serial_number": "SN-ENG-001", "location": "X",
        })
        assert res.status_code == 403

    def test_warranty_fields_saved(self, client, db):
        _, admin_hdrs = _admin(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        res = client.post("/api/v1/equipment", headers=admin_hdrs, json={
            "client_id": cl.id, "model_id": model.id,
            "serial_number": "WARR-001", "location": "Office",
            "warranty_until": "2027-12-31",
        })
        assert res.status_code == 201
        assert res.json()["warranty_until"] == "2027-12-31"


class TestGetEquipment:
    def test_get_existing(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="GET-001")
        res = client.get(f"/api/v1/equipment/{eq.id}", headers=eng_hdrs)
        assert res.status_code == 200
        assert res.json()["serial_number"] == "GET-001"

    def test_get_nonexistent_returns_404(self, client, db):
        _, eng_hdrs = _eng(db)
        res = client.get("/api/v1/equipment/999999", headers=eng_hdrs)
        assert res.status_code == 404
        assert res.json()["error"] == "NOT_FOUND"

    def test_get_deleted_returns_404(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="DEL-001")
        eq.is_deleted = True
        db.commit()
        res = client.get(f"/api/v1/equipment/{eq.id}", headers=eng_hdrs)
        assert res.status_code == 404


class TestListEquipment:
    def test_list_all_authenticated(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        make_equipment(db, cl.id, model.id, serial="LIST-001")
        res = client.get("/api/v1/equipment", headers=eng_hdrs)
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    def test_filter_by_client(self, client, db):
        _, admin_hdrs = _admin(db)
        cl1 = make_client(db, name="Client1")
        cl2 = make_client(db, name="Client2")
        model = make_equipment_model(db)
        make_equipment(db, cl1.id, model.id, serial="C1-001")
        make_equipment(db, cl2.id, model.id, serial="C2-001")
        res = client.get("/api/v1/equipment", headers=admin_hdrs, params={"client_id": cl1.id})
        for eq in res.json()["items"]:
            assert eq["client_id"] == cl1.id


class TestUpdateEquipment:
    def test_admin_updates_location(self, client, db):
        _, admin_hdrs = _admin(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id)
        res = client.put(f"/api/v1/equipment/{eq.id}", headers=admin_hdrs,
                         json={"location": "New Location 123"})
        assert res.status_code == 200
        assert res.json()["location"] == "New Location 123"

    def test_engineer_cannot_update(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id)
        res = client.put(f"/api/v1/equipment/{eq.id}", headers=eng_hdrs,
                         json={"location": "Hack"})
        assert res.status_code == 403


class TestDeleteEquipment:
    def test_admin_soft_deletes(self, client, db):
        from app.models import Equipment as EqModel
        _, admin_hdrs = _admin(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="SDEL-001")
        res = client.delete(f"/api/v1/equipment/{eq.id}", headers=admin_hdrs)
        assert res.status_code == 204
        db_eq = db.query(EqModel).filter_by(id=eq.id).first()
        assert db_eq.is_deleted is True

    def test_engineer_cannot_delete(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id)
        res = client.delete(f"/api/v1/equipment/{eq.id}", headers=eng_hdrs)
        assert res.status_code == 403


class TestEquipmentHistory:
    def test_history_endpoint_exists(self, client, db):
        _, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        assert res.status_code == 200
        assert isinstance(res.json(), list)
