"""
Tests for:
  - Comment is_internal field: filtering for client_user
  - Comment author (full_name + email) in response
  - Work act signing by client_user (row-level check)
"""
import pytest
from datetime import datetime
from app.models import User, Ticket, TicketComment, WorkAct
from tests.conftest import (
    make_admin, make_user, make_client, make_equipment_model,
    make_equipment, make_ticket, auth_headers,
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


def make_comment(db, ticket_id: int, user_id: int, text: str,
                 is_internal: bool = False) -> TicketComment:
    c = TicketComment(
        ticket_id=ticket_id,
        user_id=user_id,
        text=text,
        is_internal=is_internal,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def make_work_act(db, ticket_id: int, engineer_id: int) -> WorkAct:
    act = WorkAct(
        ticket_id=ticket_id,
        engineer_id=engineer_id,
        work_description="Repair done",
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


def _setup_basic(db):
    """Returns (admin, client_org, engineer, ticket, client_user)."""
    admin = make_admin(db)
    eng = make_user(db, email="eng@test.com", roles=["engineer"])
    org = make_client(db, name="Org-A")
    model = make_equipment_model(db)
    eq = make_equipment(db, org.id, model.id)
    ticket = Ticket(
        number="T-TEST-0001",
        client_id=org.id,
        equipment_id=eq.id,
        created_by=admin.id,
        title="Test ticket",
        type="repair",
        priority="medium",
        status="in_progress",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    cu = make_client_user(db, client_id=org.id)
    return admin, eng, org, ticket, cu


# ── Comment visibility ────────────────────────────────────────────────────────

class TestCommentVisibilityForClientUser:

    def test_client_user_does_not_see_internal_comments(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        make_comment(db, ticket.id, admin.id, "Internal note", is_internal=True)
        make_comment(db, ticket.id, eng.id, "External note", is_internal=False)

        resp = client.get(
            f"/api/v1/tickets/{ticket.id}/comments",
            headers=auth_headers(cu.id, cu.roles),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["text"] == "External note"
        assert data[0]["is_internal"] is False

    def test_admin_sees_all_comments_including_internal(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        make_comment(db, ticket.id, admin.id, "Internal note", is_internal=True)
        make_comment(db, ticket.id, eng.id, "External note", is_internal=False)

        resp = client.get(
            f"/api/v1/tickets/{ticket.id}/comments",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_client_user_comment_stored_as_external(self, client, db):
        """client_user posts is_internal=true but it gets stored as false (default)."""
        admin, eng, org, ticket, cu = _setup_basic(db)

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/comments",
            json={"text": "Hi from portal", "is_internal": False},
            headers=auth_headers(cu.id, cu.roles),
        )
        assert resp.status_code == 201
        assert resp.json()["is_internal"] is False


class TestCommentAuthorInResponse:

    def test_comment_response_includes_author_full_name(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        make_comment(db, ticket.id, eng.id, "Hello", is_internal=False)

        resp = client.get(
            f"/api/v1/tickets/{ticket.id}/comments",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        comment = resp.json()[0]
        assert "author" in comment
        assert comment["author"]["full_name"] == eng.full_name

    def test_comment_response_includes_author_email(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        make_comment(db, ticket.id, eng.id, "Hello", is_internal=False)

        resp = client.get(
            f"/api/v1/tickets/{ticket.id}/comments",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        comment = resp.json()[0]
        assert comment["author"]["email"] == eng.email

    def test_add_comment_response_includes_author(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/comments",
            json={"text": "New comment"},
            headers=auth_headers(eng.id, eng.roles),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["author"]["full_name"] == eng.full_name
        assert data["author"]["email"] == eng.email

    def test_is_internal_field_in_comment_response(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/comments",
            json={"text": "Internal remark", "is_internal": True},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 201
        assert resp.json()["is_internal"] is True


# ── Work act signing ──────────────────────────────────────────────────────────

class TestWorkActSigningByClientUser:

    def test_client_user_can_sign_work_act_for_own_org(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        act = make_work_act(db, ticket.id, eng.id)

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/work-act/{act.id}/sign",
            headers=auth_headers(cu.id, cu.roles),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["signed_by"] == cu.id
        assert data["signed_at"] is not None

    def test_client_user_cannot_sign_act_of_other_org(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        act = make_work_act(db, ticket.id, eng.id)

        # Create another org and its client_user
        other_org = make_client(db, name="Other-Org")
        other_cu = make_client_user(db, client_id=other_org.id, email="other@test.com")

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/work-act/{act.id}/sign",
            headers=auth_headers(other_cu.id, other_cu.roles),
        )
        assert resp.status_code == 403

    def test_svc_mgr_can_still_sign_act(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        act = make_work_act(db, ticket.id, eng.id)
        mgr = make_user(db, email="mgr@test.com", roles=["svc_mgr"])

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/work-act/{act.id}/sign",
            headers=auth_headers(mgr.id, mgr.roles),
        )
        assert resp.status_code == 200

    def test_double_sign_returns_400(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        act = make_work_act(db, ticket.id, eng.id)

        client.post(
            f"/api/v1/tickets/{ticket.id}/work-act/{act.id}/sign",
            headers=auth_headers(cu.id, cu.roles),
        )
        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/work-act/{act.id}/sign",
            headers=auth_headers(cu.id, cu.roles),
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "BR_VIOLATION"

    def test_engineer_cannot_sign_act(self, client, db):
        admin, eng, org, ticket, cu = _setup_basic(db)
        act = make_work_act(db, ticket.id, eng.id)

        resp = client.post(
            f"/api/v1/tickets/{ticket.id}/work-act/{act.id}/sign",
            headers=auth_headers(eng.id, eng.roles),
        )
        assert resp.status_code == 403
