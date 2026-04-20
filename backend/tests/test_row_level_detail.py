"""
Tests for row-level security on detail (get-by-id) endpoints.

client_user must NOT be able to access records of other orgs by manually
changing the ID in the URL. Expected response: HTTP 404.

Covers:
  - GET /tickets/{id}
  - GET /tickets/{id}/comments
  - GET /tickets/{id}/attachments
  - GET /tickets/{id}/work-act
  - GET /tickets/{id}/status-history
  - POST /tickets/{id}/comments
  - GET /clients/{id}
  - GET /equipment/{id}
  - GET /equipment/{id}/history
"""
import pytest
from app.models import User, Client, Equipment, EquipmentModel, Ticket, WorkAct
from tests.conftest import (
    make_admin, make_user, make_client, make_equipment_model,
    make_equipment, auth_headers,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_client_user(db, client_id: int, email: str = "cu@test.com") -> User:
    u = User(
        email=email,
        full_name="Portal User",
        password_hash="hashed",
        roles=["client_user"],
        client_id=client_id,
        is_active=True,
        is_deleted=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_ticket_obj(db, client_id: int, created_by: int, number: str) -> Ticket:
    t = Ticket(
        number=number,
        client_id=client_id,
        created_by=created_by,
        title="Test",
        type="repair",
        priority="medium",
        status="new",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def make_work_act(db, ticket_id: int, engineer_id: int) -> WorkAct:
    act = WorkAct(ticket_id=ticket_id, engineer_id=engineer_id, work_description="done")
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


def _setup(db):
    """
    Two orgs, each with one ticket and one equipment unit.
    Returns (admin, org_a, org_b, ticket_a, ticket_b, eq_a, eq_b, cu_a).
    cu_a belongs to org_a.
    """
    admin = make_admin(db)
    org_a = make_client(db, name="Org-A")
    org_b = make_client(db, name="Org-B")
    model = make_equipment_model(db)
    eq_a = make_equipment(db, org_a.id, model.id, serial="SN-A")
    eq_b = make_equipment(db, org_b.id, model.id, serial="SN-B")
    ticket_a = make_ticket_obj(db, org_a.id, admin.id, "T-OWN-001")
    ticket_b = make_ticket_obj(db, org_b.id, admin.id, "T-OTH-001")
    cu_a = make_client_user(db, client_id=org_a.id)
    return admin, org_a, org_b, ticket_a, ticket_b, eq_a, eq_b, cu_a


# ── Ticket detail ─────────────────────────────────────────────────────────────

class TestTicketDetailRowLevel:

    def test_client_user_can_get_own_ticket(self, client, db):
        _, _, _, ticket_a, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/tickets/{ticket_a.id}",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == ticket_a.id

    def test_client_user_cannot_get_other_org_ticket(self, client, db):
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_cannot_get_comments_of_other_org_ticket(self, client, db):
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}/comments",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_cannot_post_comment_to_other_org_ticket(self, client, db):
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.post(
            f"/api/v1/tickets/{ticket_b.id}/comments",
            json={"text": "hello"},
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_cannot_get_attachments_of_other_org_ticket(self, client, db):
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}/attachments",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_cannot_get_status_history_of_other_org_ticket(self, client, db):
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}/status-history",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_cannot_get_work_act_of_other_org_ticket(self, client, db):
        admin, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        make_work_act(db, ticket_b.id, admin.id)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}/work-act",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_admin_can_get_any_ticket(self, client, db):
        admin, _, _, _, ticket_b, _, _, _ = _setup(db)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200


# ── Client detail ─────────────────────────────────────────────────────────────

class TestClientDetailRowLevel:

    def test_client_user_can_get_own_org(self, client, db):
        _, org_a, _, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_a.id}",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == org_a.id

    def test_client_user_cannot_get_other_org(self, client, db):
        _, _, org_b, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_b.id}",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_admin_can_get_any_client(self, client, db):
        admin, _, org_b, _, _, _, _, _ = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_b.id}",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200


# ── Equipment detail ──────────────────────────────────────────────────────────

class TestEquipmentDetailRowLevel:

    def test_client_user_can_get_own_equipment(self, client, db):
        _, _, _, _, _, eq_a, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/equipment/{eq_a.id}",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == eq_a.id

    def test_client_user_cannot_get_other_org_equipment(self, client, db):
        _, _, _, _, _, _, eq_b, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/equipment/{eq_b.id}",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_cannot_get_history_of_other_org_equipment(self, client, db):
        _, _, _, _, _, _, eq_b, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/equipment/{eq_b.id}/history",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_admin_can_get_any_equipment(self, client, db):
        admin, _, _, _, _, _, eq_b, _ = _setup(db)
        resp = client.get(
            f"/api/v1/equipment/{eq_b.id}",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
