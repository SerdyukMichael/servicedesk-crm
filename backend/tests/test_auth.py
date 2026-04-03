"""
Unit tests — POST /api/v1/auth/login & GET /api/v1/auth/me
"""
import pytest
from tests.conftest import make_user, make_admin


class TestLogin:
    def test_login_success(self, client, db):
        make_user(db, email="eng@test.com", password="pass12345", roles=["engineer"])
        res = client.post("/api/v1/auth/login", json={"email": "eng@test.com", "password": "pass12345"})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["email"] == "eng@test.com"
        assert "engineer" in data["roles"]

    def test_login_wrong_password(self, client, db):
        make_user(db, email="eng@test.com", password="correct")
        res = client.post("/api/v1/auth/login", json={"email": "eng@test.com", "password": "wrong"})
        assert res.status_code == 401

    def test_login_unknown_email(self, client, db):
        res = client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "x"})
        assert res.status_code == 401

    def test_login_inactive_user(self, client, db):
        make_user(db, email="inactive@test.com", password="pass", is_active=False)
        res = client.post("/api/v1/auth/login", json={"email": "inactive@test.com", "password": "pass"})
        assert res.status_code == 401

    def test_login_missing_fields(self, client, db):
        res = client.post("/api/v1/auth/login", json={"email": "x@x.com"})
        assert res.status_code == 422

    def test_login_empty_password(self, client, db):
        make_user(db, email="eng@test.com", password="real_pass")
        res = client.post("/api/v1/auth/login", json={"email": "eng@test.com", "password": ""})
        assert res.status_code == 401

    def test_login_returns_user_id(self, client, db):
        u = make_user(db, email="eng@test.com", password="pass12345")
        res = client.post("/api/v1/auth/login", json={"email": "eng@test.com", "password": "pass12345"})
        assert res.json()["user_id"] == u.id

    def test_login_admin_has_admin_role(self, client, db):
        make_admin(db, email="admin@test.com", password="admin12345")
        res = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "admin12345"})
        assert res.status_code == 200
        assert "admin" in res.json()["roles"]


class TestGetMe:
    def _login(self, client, db, email="me@test.com", password="pass123"):
        make_user(db, email=email, password=password)
        res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        return res.json()["access_token"]

    def test_get_me_success(self, client, db):
        token = self._login(client, db)
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["email"] == "me@test.com"

    def test_get_me_no_token(self, client, db):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_get_me_invalid_token(self, client, db):
        res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
        assert res.status_code == 401

    def test_get_me_returns_roles(self, client, db):
        make_user(db, email="eng@test.com", password="pass", roles=["engineer", "warehouse"])
        res = client.post("/api/v1/auth/login", json={"email": "eng@test.com", "password": "pass"})
        token = res.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert "engineer" in me["roles"]
        assert "warehouse" in me["roles"]
