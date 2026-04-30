"""
Unit tests — /api/v1/users
Covers: CRUD, RBAC, soft-delete, duplicate email, pagination.
"""
import pytest
from tests.conftest import (
    make_admin, make_svc_mgr, make_engineer, make_user,
    auth_headers,
)


def _admin_token(db):
    u = make_admin(db)
    return auth_headers(u.id, u.roles)


def _engineer_token(db):
    u = make_engineer(db)
    return auth_headers(u.id, u.roles)


def _svc_mgr_token(db):
    u = make_svc_mgr(db)
    return auth_headers(u.id, u.roles)


class TestListUsers:
    def test_admin_can_list(self, client, db):
        headers = _admin_token(db)
        res = client.get("/api/v1/users", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_svc_mgr_can_list(self, client, db):
        headers = _svc_mgr_token(db)
        res = client.get("/api/v1/users", headers=headers)
        assert res.status_code == 200

    def test_engineer_cannot_list(self, client, db):
        headers = _engineer_token(db)
        res = client.get("/api/v1/users", headers=headers)
        assert res.status_code == 403

    def test_unauthenticated_cannot_list(self, client, db):
        res = client.get("/api/v1/users")
        assert res.status_code == 401

    def test_pagination_limit(self, client, db):
        headers = _admin_token(db)
        # create 5 more users
        for i in range(5):
            make_user(db, email=f"u{i}@test.com", roles=["engineer"])
        res = client.get("/api/v1/users", headers=headers, params={"size": 2})
        data = res.json()
        assert len(data["items"]) <= 2
        assert data["pages"] >= 1

    def test_filter_by_role(self, client, db):
        admin = make_admin(db)
        make_user(db, email="e1@test.com", roles=["engineer"])
        make_user(db, email="e2@test.com", roles=["engineer"])
        headers = auth_headers(admin.id, admin.roles)
        res = client.get("/api/v1/users", headers=headers, params={"role": "engineer"})
        assert res.status_code == 200
        for u in res.json()["items"]:
            roles = u["roles"]
            assert "engineer" in roles


class TestCreateUser:
    def test_admin_creates_user(self, client, db):
        headers = _admin_token(db)
        res = client.post("/api/v1/users", headers=headers, json={
            "email": "new@test.com",
            "full_name": "New User",
            "password": "pass12345",
            "roles": ["engineer"],
        })
        assert res.status_code == 201
        assert res.json()["email"] == "new@test.com"

    def test_duplicate_email_returns_409(self, client, db):
        headers = _admin_token(db)
        payload = {"email": "dup@test.com", "full_name": "A", "password": "p12345678", "roles": ["engineer"]}
        client.post("/api/v1/users", headers=headers, json=payload)
        res = client.post("/api/v1/users", headers=headers, json=payload)
        assert res.status_code == 409
        assert res.json()["error"] == "CONFLICT"

    def test_engineer_cannot_create_user(self, client, db):
        headers = _engineer_token(db)
        res = client.post("/api/v1/users", headers=headers, json={
            "email": "x@test.com", "full_name": "X", "password": "p12345", "roles": ["engineer"],
        })
        assert res.status_code == 403

    def test_missing_required_fields_returns_422(self, client, db):
        headers = _admin_token(db)
        res = client.post("/api/v1/users", headers=headers, json={"email": "x@test.com"})
        assert res.status_code == 422

    def test_created_user_has_correct_role(self, client, db):
        headers = _admin_token(db)
        res = client.post("/api/v1/users", headers=headers, json={
            "email": "wh@test.com", "full_name": "WH", "password": "p12345678", "roles": ["warehouse"],
        })
        assert res.status_code == 201
        assert "warehouse" in res.json()["roles"]


class TestGetUser:
    def test_get_existing_user(self, client, db):
        admin = make_admin(db)
        user = make_user(db, email="target@test.com")
        headers = auth_headers(admin.id, admin.roles)
        res = client.get(f"/api/v1/users/{user.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["email"] == "target@test.com"

    def test_get_nonexistent_user_404(self, client, db):
        headers = _admin_token(db)
        res = client.get("/api/v1/users/999999", headers=headers)
        assert res.status_code == 404
        assert res.json()["error"] == "NOT_FOUND"

    def test_get_deleted_user_404(self, client, db):
        admin = make_admin(db)
        user = make_user(db, email="gone@test.com")
        user.is_deleted = True
        db.commit()
        headers = auth_headers(admin.id, admin.roles)
        res = client.get(f"/api/v1/users/{user.id}", headers=headers)
        assert res.status_code == 404


class TestUpdateUser:
    def test_admin_can_update(self, client, db):
        admin = make_admin(db)
        user = make_user(db, email="upd@test.com")
        headers = auth_headers(admin.id, admin.roles)
        res = client.put(f"/api/v1/users/{user.id}", headers=headers,
                         json={"full_name": "Updated Name"})
        assert res.status_code == 200
        assert res.json()["full_name"] == "Updated Name"

    def test_engineer_cannot_update(self, client, db):
        eng = make_engineer(db)
        target = make_user(db, email="target@test.com")
        headers = auth_headers(eng.id, eng.roles)
        res = client.put(f"/api/v1/users/{target.id}", headers=headers,
                         json={"full_name": "Hacked"})
        assert res.status_code == 403


class TestDeleteUser:
    def test_soft_delete_marks_is_deleted(self, client, db):
        admin = make_admin(db)
        user = make_user(db, email="del@test.com")
        headers = auth_headers(admin.id, admin.roles)
        res = client.delete(f"/api/v1/users/{user.id}", headers=headers)
        assert res.status_code == 204
        db.refresh(user)
        assert user.is_deleted is True

    def test_cannot_delete_self(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        res = client.delete(f"/api/v1/users/{admin.id}", headers=headers)
        assert res.status_code == 400
        assert "CANNOT_DELETE_SELF" in res.json()["error"]

    def test_deleted_user_returns_404_on_get(self, client, db):
        admin = make_admin(db)
        user = make_user(db, email="del2@test.com")
        headers = auth_headers(admin.id, admin.roles)
        client.delete(f"/api/v1/users/{user.id}", headers=headers)
        res = client.get(f"/api/v1/users/{user.id}", headers=headers)
        assert res.status_code == 404

    def test_engineer_cannot_delete(self, client, db):
        eng = make_engineer(db)
        target = make_user(db, email="target@test.com")
        headers = auth_headers(eng.id, eng.roles)
        res = client.delete(f"/api/v1/users/{target.id}", headers=headers)
        assert res.status_code == 403
