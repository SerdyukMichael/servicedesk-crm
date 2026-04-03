"""
Tests for security fixes: S-04, S-05, S-06, S-11.

S-04: Authenticated download endpoint — anonymous access must return 401
S-05: client_user cannot update/assign tickets of other orgs
S-06: client_user cannot list contacts/equipment/tickets of other orgs via sub-resources
S-11: change_ticket_status requires role; client_user limited to own org's tickets
"""
import pytest
from app.models import User, Ticket, TicketFile
from tests.conftest import (
    make_admin, make_user, make_client, make_equipment_model,
    make_equipment, make_ticket, auth_headers,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_client_user(db, client_id: int, email: str = "cu@sec.com") -> User:
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


def make_ticket_file(db, ticket_id: int, uploader_id: int) -> TicketFile:
    f = TicketFile(
        ticket_id=ticket_id,
        uploaded_by=uploader_id,
        file_name="test.txt",
        file_type="text/plain",
        file_size=4,
        file_data=b"test",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _setup(db):
    """
    Two orgs (A and B), each with a ticket and an equipment unit.
    Returns (admin, org_a, org_b, ticket_a, ticket_b, eq_a, eq_b, cu_a).
    cu_a belongs to org_a.
    """
    admin = make_admin(db)
    org_a = make_client(db, name="Org-A-Sec")
    org_b = make_client(db, name="Org-B-Sec")
    model = make_equipment_model(db, name="Model-Sec")
    eq_a = make_equipment(db, org_a.id, model.id, serial="SEC-A")
    eq_b = make_equipment(db, org_b.id, model.id, serial="SEC-B")
    ticket_a = make_ticket(db, org_a.id, eq_a.id, admin.id)
    ticket_b = _make_ticket_b(db, org_b.id, eq_b.id, admin.id)
    cu_a = make_client_user(db, client_id=org_a.id)
    return admin, org_a, org_b, ticket_a, ticket_b, eq_a, eq_b, cu_a


def _make_ticket_b(db, client_id, equipment_id, created_by):
    from datetime import datetime, timedelta
    t = Ticket(
        number="T-SEC-B-001",
        client_id=client_id,
        equipment_id=equipment_id,
        created_by=created_by,
        title="Ticket B",
        type="repair",
        priority="medium",
        status="new",
        sla_deadline=datetime.utcnow() + timedelta(hours=24),
        is_deleted=False,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ── S-04: Authenticated download ──────────────────────────────────────────────

class TestAuthenticatedDownload:

    def test_anonymous_download_returns_401(self, client, db):
        """S-04: /download endpoint must reject unauthenticated requests."""
        admin, _, _, ticket_a, _, _, _, _ = _setup(db)
        f = make_ticket_file(db, ticket_a.id, admin.id)
        resp = client.get(f"/api/v1/tickets/{ticket_a.id}/attachments/{f.id}/download")
        assert resp.status_code == 401

    def test_authenticated_user_can_download_own_ticket_file(self, client, db):
        """S-04: Authenticated user can download file from own ticket."""
        admin, _, _, ticket_a, _, _, _, _ = _setup(db)
        f = make_ticket_file(db, ticket_a.id, admin.id)
        resp = client.get(
            f"/api/v1/tickets/{ticket_a.id}/attachments/{f.id}/download",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        assert resp.content == b"test"

    def test_client_user_cannot_download_other_org_file(self, client, db):
        """S-04: client_user cannot download files from other org's ticket."""
        admin, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        f = make_ticket_file(db, ticket_b.id, admin.id)
        resp = client.get(
            f"/api/v1/tickets/{ticket_b.id}/attachments/{f.id}/download",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_can_download_own_org_file(self, client, db):
        """S-04: client_user can download file from own org's ticket."""
        admin, _, _, ticket_a, _, _, _, cu_a = _setup(db)
        f = make_ticket_file(db, ticket_a.id, admin.id)
        resp = client.get(
            f"/api/v1/tickets/{ticket_a.id}/attachments/{f.id}/download",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200


# ── S-05: Update/assign ticket row-level ──────────────────────────────────────

class TestTicketUpdateRowLevel:

    def test_client_user_cannot_update_other_org_ticket(self, client, db):
        """S-05: client_user cannot PUT /tickets/{other_org_ticket_id}."""
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.put(
            f"/api/v1/tickets/{ticket_b.id}",
            json={"title": "Hacked"},
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_can_update_own_org_ticket(self, client, db):
        """S-05: client_user can update own org's ticket."""
        _, _, _, ticket_a, _, _, _, cu_a = _setup(db)
        resp = client.put(
            f"/api/v1/tickets/{ticket_a.id}",
            json={"title": "Updated by portal user"},
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated by portal user"

    def test_client_user_cannot_assign_ticket(self, client, db):
        """S-05: client_user cannot assign any ticket (role not in assign_ticket)."""
        _, _, _, ticket_a, _, _, _, cu_a = _setup(db)
        admin = make_admin(db, email="admin2@test.com")
        resp = client.patch(
            f"/api/v1/tickets/{ticket_a.id}/assign",
            json={"engineer_id": admin.id},
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 403

    def test_admin_can_assign_any_ticket(self, client, db):
        """S-05: admin can assign any ticket."""
        admin, _, _, ticket_a, _, _, _, _ = _setup(db)
        engineer = make_user(db, email="eng2@test.com", roles=["engineer"])
        resp = client.patch(
            f"/api/v1/tickets/{ticket_a.id}/assign",
            json={"engineer_id": engineer.id},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200


# ── S-06: Client sub-resources row-level ──────────────────────────────────────

class TestClientSubResourceRowLevel:

    def test_client_user_cannot_list_contacts_of_other_org(self, client, db):
        """S-06: client_user cannot GET /clients/{other_org_id}/contacts."""
        _, _, org_b, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_b.id}/contacts",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_can_list_own_org_contacts(self, client, db):
        """S-06: client_user can GET /clients/{own_org_id}/contacts."""
        _, org_a, _, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_a.id}/contacts",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200

    def test_client_user_cannot_list_equipment_of_other_org(self, client, db):
        """S-06: client_user cannot GET /clients/{other_org_id}/equipment."""
        _, _, org_b, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_b.id}/equipment",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_can_list_own_org_equipment(self, client, db):
        """S-06: client_user can GET /clients/{own_org_id}/equipment."""
        _, org_a, _, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_a.id}/equipment",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200

    def test_client_user_cannot_list_tickets_of_other_org(self, client, db):
        """S-06: client_user cannot GET /clients/{other_org_id}/tickets."""
        _, _, org_b, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_b.id}/tickets",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_can_list_own_org_tickets(self, client, db):
        """S-06: client_user can GET /clients/{own_org_id}/tickets."""
        _, org_a, _, _, _, _, _, cu_a = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_a.id}/tickets",
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200

    def test_admin_can_list_any_client_contacts(self, client, db):
        """S-06: admin can access sub-resources of any org."""
        admin, _, org_b, _, _, _, _, _ = _setup(db)
        resp = client.get(
            f"/api/v1/clients/{org_b.id}/contacts",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200


# ── S-11: change_ticket_status authorization ──────────────────────────────────

class TestChangeTicketStatusAuth:

    def test_anonymous_cannot_change_status(self, client, db):
        """S-11: unauthenticated request returns 401."""
        _, _, _, ticket_a, _, _, _, _ = _setup(db)
        resp = client.patch(
            f"/api/v1/tickets/{ticket_a.id}/status",
            json={"status": "cancelled"},
        )
        assert resp.status_code == 401

    def test_client_user_cannot_change_status_of_other_org_ticket(self, client, db):
        """S-11: client_user cannot change status of other org's ticket."""
        _, _, _, _, ticket_b, _, _, cu_a = _setup(db)
        resp = client.patch(
            f"/api/v1/tickets/{ticket_b.id}/status",
            json={"status": "cancelled"},
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 404

    def test_client_user_can_cancel_own_org_ticket(self, client, db):
        """S-11: client_user can cancel own org's ticket (valid FSM transition)."""
        _, _, _, ticket_a, _, _, _, cu_a = _setup(db)
        resp = client.patch(
            f"/api/v1/tickets/{ticket_a.id}/status",
            json={"status": "cancelled"},
            headers=auth_headers(cu_a.id, cu_a.roles),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_engineer_can_change_status(self, client, db):
        """S-11: engineer role is allowed to change ticket status."""
        admin, org_a, _, ticket_a, _, _, _, _ = _setup(db)
        engineer = make_user(db, email="eng3@test.com", roles=["engineer"])
        # First assign the ticket
        ticket_a.assigned_to = engineer.id
        ticket_a.status = "assigned"
        db.commit()
        resp = client.patch(
            f"/api/v1/tickets/{ticket_a.id}/status",
            json={"status": "in_progress"},
            headers=auth_headers(engineer.id, engineer.roles),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_warehouse_role_cannot_change_status(self, client, db):
        """S-11: warehouse role is not allowed to change ticket status."""
        _, _, _, ticket_a, _, _, _, _ = _setup(db)
        warehouse = make_user(db, email="wh@test.com", roles=["warehouse"])
        resp = client.patch(
            f"/api/v1/tickets/{ticket_a.id}/status",
            json={"status": "cancelled"},
            headers=auth_headers(warehouse.id, warehouse.roles),
        )
        assert resp.status_code == 403
