"""
Unit tests — /api/v1/work-templates
Covers: CRUD, пустые шаги (BR), фильтр по модели, RBAC.
"""
import pytest
from tests.conftest import (
    make_admin, make_engineer, make_user, make_work_template,
    make_equipment_model,
    auth_headers,
)


def _admin(db):
    u = make_admin(db)
    return u, auth_headers(u.id, u.roles)


def _svc(db):
    u = make_user(db, email="svc@t.com", roles=["svc_mgr"])
    return u, auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db)
    return u, auth_headers(u.id, u.roles)


class TestCreateTemplate:
    def test_admin_creates_template(self, client, db):
        u, admin_hdrs = _admin(db)
        model = make_equipment_model(db, name="NCR 6683")
        res = client.post("/api/v1/work-templates", headers=admin_hdrs, json={
            "name": "ТО NCR 6683",
            "equipment_model_id": model.id,
            "steps": [
                {"step_order": 1, "description": "Чистка механизма"},
                {"step_order": 2, "description": "Замена бумаги"},
            ],
        })
        assert res.status_code == 201
        assert res.json()["name"] == "ТО NCR 6683"

    def test_svc_mgr_creates_template(self, client, db):
        _, svc_hdrs = _svc(db)
        model = make_equipment_model(db, name="Matica XID")
        res = client.post("/api/v1/work-templates", headers=svc_hdrs, json={
            "name": "ТО Matica",
            "equipment_model_id": model.id,
            "steps": [{"step_order": 1, "description": "Чистка"}],
        })
        assert res.status_code == 201

    def test_empty_steps_rejected(self, client, db):
        """BR: Шаблон без шагов недопустим."""
        _, admin_hdrs = _admin(db)
        model = make_equipment_model(db, name="Test Model Empty")
        res = client.post("/api/v1/work-templates", headers=admin_hdrs, json={
            "name": "Пустой шаблон",
            "equipment_model_id": model.id,
            "steps": [],
        })
        assert res.status_code in (400, 422)

    def test_engineer_cannot_create(self, client, db):
        _, eng_hdrs = _eng(db)
        model = make_equipment_model(db, name="Eng Model")
        res = client.post("/api/v1/work-templates", headers=eng_hdrs, json={
            "name": "Test",
            "equipment_model_id": model.id,
            "steps": [{"step_order": 1, "description": "Step"}],
        })
        assert res.status_code == 403


class TestGetTemplate:
    def test_get_existing(self, client, db):
        u, admin_hdrs = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        res = client.get(f"/api/v1/work-templates/{tmpl.id}", headers=admin_hdrs)
        assert res.status_code == 200
        assert res.json()["id"] == tmpl.id

    def test_get_nonexistent_returns_404(self, client, db):
        _, admin_hdrs = _admin(db)
        res = client.get("/api/v1/work-templates/999999", headers=admin_hdrs)
        assert res.status_code == 404

    def test_engineer_can_view(self, client, db):
        u, _ = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        _, eng_hdrs = _eng(db)
        res = client.get(f"/api/v1/work-templates/{tmpl.id}", headers=eng_hdrs)
        assert res.status_code == 200


class TestListTemplates:
    def test_list_all(self, client, db):
        u, admin_hdrs = _admin(db)
        make_work_template(db, created_by=u.id)
        res = client.get("/api/v1/work-templates", headers=admin_hdrs)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data or isinstance(data, list)

    def test_filter_by_model_id(self, client, db):
        u, admin_hdrs = _admin(db)
        model = make_equipment_model(db, name="Filter Model")
        from app.models import WorkTemplate, WorkTemplateStep
        tmpl = WorkTemplate(name="Filter Test", equipment_model_id=model.id,
                            is_active=True, created_by=u.id)
        db.add(tmpl)
        db.commit()
        db.refresh(tmpl)
        step = WorkTemplateStep(template_id=tmpl.id, step_order=1, description="S1")
        db.add(step)
        db.commit()
        res = client.get("/api/v1/work-templates", headers=admin_hdrs,
                         params={"equipment_model_id": model.id})
        assert res.status_code == 200
        items = res.json().get("items", res.json())
        for t in items:
            assert t["equipment_model_id"] == model.id


class TestUpdateTemplate:
    def test_admin_updates_name(self, client, db):
        u, admin_hdrs = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        res = client.put(f"/api/v1/work-templates/{tmpl.id}", headers=admin_hdrs,
                         json={"name": "Updated Name"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Name"

    def test_engineer_cannot_update(self, client, db):
        u, _ = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        _, eng_hdrs = _eng(db)
        res = client.put(f"/api/v1/work-templates/{tmpl.id}", headers=eng_hdrs,
                         json={"name": "Hacked"})
        assert res.status_code == 403


class TestDeleteTemplate:
    def test_admin_deletes_template(self, client, db):
        u, admin_hdrs = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        res = client.delete(f"/api/v1/work-templates/{tmpl.id}", headers=admin_hdrs)
        assert res.status_code == 204

    def test_deleted_template_returns_404(self, client, db):
        u, admin_hdrs = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        client.delete(f"/api/v1/work-templates/{tmpl.id}", headers=admin_hdrs)
        res = client.get(f"/api/v1/work-templates/{tmpl.id}", headers=admin_hdrs)
        assert res.status_code == 404

    def test_engineer_cannot_delete(self, client, db):
        u, _ = _admin(db)
        tmpl = make_work_template(db, created_by=u.id)
        _, eng_hdrs = _eng(db)
        res = client.delete(f"/api/v1/work-templates/{tmpl.id}", headers=eng_hdrs)
        assert res.status_code == 403
