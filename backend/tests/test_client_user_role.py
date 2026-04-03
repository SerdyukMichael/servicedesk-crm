"""
Tests for client_user role:
  - Portal access: grant creates User with client_user role + correct client_id
  - Portal access: revoke deactivates the linked User
  - Row-level filtering: client_user sees only their own org data
  - Parts: client_user gets 403
"""
import pytest
from app.models import User, Client, ClientContact
from tests.conftest import (
    make_admin, make_user, make_client, make_equipment_model, make_equipment,
    make_ticket, make_spare_part,
    auth_headers,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_contact(db, client_id: int, name: str = "Test Contact",
                 email: str = "contact@test.com", is_active: bool = True) -> ClientContact:
    c = ClientContact(
        client_id=client_id,
        name=name,
        email=email,
        is_active=is_active,
        is_primary=False,
        portal_access=False,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def make_client_user(db, client_id: int,
                     email: str = "client_user@test.com") -> User:
    u = User(
        email=email,
        full_name="Client Portal User",
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


def _admin_hdrs(db) -> dict:
    u = make_admin(db)
    return auth_headers(u.id, u.roles)


def _sales_hdrs(db) -> dict:
    u = make_user(db, email="sales@test.com", roles=["sales_mgr"])
    return auth_headers(u.id, u.roles)


# ── Portal access: grant ───────────────────────────────────────────────────────

class TestGrantPortalAccess:
    def test_grant_creates_new_user(self, client, db):
        """Grant portal access → creates a new User with client_user role."""
        cl = make_client(db)
        contact = make_contact(db, cl.id, email="portal@bank.com")
        hdrs = _sales_hdrs(db)

        res = client.post(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            json={"portal_role": "client_user"},
            headers=hdrs,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["portal_access"] is True
        assert data["portal_role"] == "client_user"
        assert data["portal_user_id"] is not None
        # Temp password returned in response
        assert "temporary_password" in data
        assert data["temporary_password"] is not None

        # Verify User was created in DB
        portal_user = db.query(User).filter(User.email == "portal@bank.com").first()
        assert portal_user is not None
        assert "client_user" in portal_user.roles
        assert portal_user.client_id == cl.id
        assert portal_user.is_active is True
        assert portal_user.is_deleted is False

    def test_grant_with_custom_email(self, client, db):
        """Grant with different email → uses provided email for new user."""
        cl = make_client(db)
        contact = make_contact(db, cl.id, email=None)
        hdrs = _admin_hdrs(db)

        res = client.post(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            json={"portal_role": "client_user", "email": "custom@bank.kz"},
            headers=hdrs,
        )
        assert res.status_code == 200
        portal_user = db.query(User).filter(User.email == "custom@bank.kz").first()
        assert portal_user is not None
        assert portal_user.client_id == cl.id

    def test_grant_existing_user_reactivates(self, client, db):
        """Grant to contact whose email already has a deactivated User → reactivates it."""
        cl = make_client(db)
        # Pre-create an inactive user with that email
        existing = User(
            email="reactivate@bank.com",
            full_name="Old User",
            password_hash="x",
            roles=["engineer"],
            is_active=False,
            is_deleted=True,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

        contact = make_contact(db, cl.id, email="reactivate@bank.com")
        hdrs = _admin_hdrs(db)

        res = client.post(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            json={"portal_role": "client_user"},
            headers=hdrs,
        )
        assert res.status_code == 200
        db.refresh(existing)
        assert existing.is_active is True
        assert existing.is_deleted is False
        assert existing.client_id == cl.id
        assert "client_user" in existing.roles

    def test_grant_inactive_contact_returns_422(self, client, db):
        """Cannot grant portal access to an inactive contact."""
        cl = make_client(db)
        contact = make_contact(db, cl.id, email="inactive@bank.com", is_active=False)
        hdrs = _admin_hdrs(db)

        res = client.post(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            json={"portal_role": "client_user"},
            headers=hdrs,
        )
        assert res.status_code == 422
        assert res.json()["error"] == "CONTACT_INACTIVE"

    def test_grant_no_email_returns_422(self, client, db):
        """Contact with no email and no email in payload → 422."""
        cl = make_client(db)
        contact = make_contact(db, cl.id, email=None)
        hdrs = _admin_hdrs(db)

        res = client.post(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            json={"portal_role": "client_user"},
            headers=hdrs,
        )
        assert res.status_code == 422
        assert res.json()["error"] == "EMAIL_REQUIRED"

    def test_grant_engineer_forbidden(self, client, db):
        """Engineer cannot grant portal access."""
        cl = make_client(db)
        contact = make_contact(db, cl.id, email="eng@bank.com")
        u = make_user(db, email="eng@test.com", roles=["engineer"])
        hdrs = auth_headers(u.id, u.roles)

        res = client.post(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            json={"portal_role": "client_user"},
            headers=hdrs,
        )
        assert res.status_code == 403


# ── Portal access: revoke ─────────────────────────────────────────────────────

class TestRevokePortalAccess:
    def test_revoke_deactivates_linked_user(self, client, db):
        """Revoke portal access → linked User.is_active becomes False."""
        cl = make_client(db)
        portal_user = make_client_user(db, cl.id, "linked@bank.com")
        contact = make_contact(db, cl.id, email="linked@bank.com")
        contact.portal_access = True
        contact.portal_role = "client_user"
        contact.portal_user_id = portal_user.id
        db.commit()

        hdrs = _admin_hdrs(db)
        res = client.delete(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            headers=hdrs,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["portal_access"] is False
        assert data["portal_role"] is None

        db.refresh(portal_user)
        assert portal_user.is_active is False

    def test_revoke_no_linked_user_is_ok(self, client, db):
        """Revoke when no portal_user_id → just clears flag, no error."""
        cl = make_client(db)
        contact = make_contact(db, cl.id)
        contact.portal_access = True
        db.commit()

        hdrs = _admin_hdrs(db)
        res = client.delete(
            f"/api/v1/clients/{cl.id}/contacts/{contact.id}/portal-access",
            headers=hdrs,
        )
        assert res.status_code == 200
        assert res.json()["portal_access"] is False


# ── Row-level filtering for client_user ──────────────────────────────────────

class TestClientUserFiltering:
    """client_user sees only their own organisation's data."""

    def _make_client_user_hdrs(self, db, client_id: int, email: str = "cu@bank.com") -> dict:
        u = make_client_user(db, client_id, email=email)
        return auth_headers(u.id, u.roles)

    def test_list_clients_sees_only_own_org(self, client, db):
        cl_own = make_client(db, name="Own Bank")
        cl_other = make_client(db, name="Other Bank")
        hdrs = self._make_client_user_hdrs(db, cl_own.id)

        res = client.get("/api/v1/clients", headers=hdrs)
        assert res.status_code == 200
        names = [c["name"] for c in res.json()["items"]]
        assert "Own Bank" in names
        assert "Other Bank" not in names

    def test_list_equipment_sees_only_own_org(self, client, db):
        cl_own = make_client(db, name="Own Bank E")
        cl_other = make_client(db, name="Other Bank E")
        m = make_equipment_model(db)
        eq_own = make_equipment(db, cl_own.id, m.id, serial="SN-OWN")
        eq_other = make_equipment(db, cl_other.id, m.id, serial="SN-OTHER")
        hdrs = self._make_client_user_hdrs(db, cl_own.id, email="cu_eq@bank.com")

        res = client.get("/api/v1/equipment", headers=hdrs)
        assert res.status_code == 200
        serials = [e["serial_number"] for e in res.json()["items"]]
        assert "SN-OWN" in serials
        assert "SN-OTHER" not in serials

    def test_list_tickets_sees_only_own_org(self, client, db):
        from datetime import datetime
        from app.models import Ticket as TicketModel

        cl_own = make_client(db, name="Own Bank T")
        cl_other = make_client(db, name="Other Bank T")
        admin = make_admin(db)
        m = make_equipment_model(db, name="M-Ticket")
        eq_own = make_equipment(db, cl_own.id, m.id, serial="SN-T-OWN")
        eq_other = make_equipment(db, cl_other.id, m.id, serial="SN-T-OTH")

        from datetime import timedelta
        now = datetime.utcnow()
        t_own = TicketModel(
            number="T-OWN-0001", client_id=cl_own.id, equipment_id=eq_own.id,
            created_by=admin.id, title="Own Ticket", type="repair",
            priority="medium", status="new",
            sla_deadline=now + timedelta(hours=24),
        )
        t_other = TicketModel(
            number="T-OTH-0001", client_id=cl_other.id, equipment_id=eq_other.id,
            created_by=admin.id, title="Other Ticket", type="repair",
            priority="medium", status="new",
            sla_deadline=now + timedelta(hours=24),
        )
        db.add_all([t_own, t_other])
        db.commit()
        db.refresh(t_own)
        db.refresh(t_other)
        hdrs = self._make_client_user_hdrs(db, cl_own.id, email="cu_tick@bank.com")

        res = client.get("/api/v1/tickets", headers=hdrs)
        assert res.status_code == 200
        ticket_ids = [t["id"] for t in res.json()["items"]]
        assert t_own.id in ticket_ids
        assert t_other.id not in ticket_ids

    def test_list_invoices_sees_only_own_org(self, client, db):
        from decimal import Decimal
        from app.models import Invoice
        from datetime import date

        cl_own = make_client(db, name="Own Bank I")
        cl_other = make_client(db, name="Other Bank I")
        admin = make_admin(db, email="admin_inv@test.com")

        inv_own = Invoice(
            number="INV-2024-00001", client_id=cl_own.id,
            type="service", status="draft",
            issue_date=date.today(),
            subtotal=Decimal("0"), vat_amount=Decimal("0"),
            total_amount=Decimal("0"), vat_rate=Decimal("12"),
            created_by=admin.id,
        )
        inv_other = Invoice(
            number="INV-2024-00002", client_id=cl_other.id,
            type="service", status="draft",
            issue_date=date.today(),
            subtotal=Decimal("0"), vat_amount=Decimal("0"),
            total_amount=Decimal("0"), vat_rate=Decimal("12"),
            created_by=admin.id,
        )
        db.add_all([inv_own, inv_other])
        db.commit()
        db.refresh(inv_own)
        db.refresh(inv_other)

        hdrs = self._make_client_user_hdrs(db, cl_own.id, email="cu_inv@bank.com")
        res = client.get("/api/v1/invoices", headers=hdrs)
        assert res.status_code == 200
        ids = [i["id"] for i in res.json()["items"]]
        assert inv_own.id in ids
        assert inv_other.id not in ids

    def test_list_users_sees_only_same_client(self, client, db):
        cl_own = make_client(db, name="Own Bank U")
        cl_other = make_client(db, name="Other Bank U")
        u_same = make_client_user(db, cl_own.id, email="same@bank.com")
        u_other = make_client_user(db, cl_other.id, email="other@bank.com")
        hdrs = self._make_client_user_hdrs(db, cl_own.id, email="cu_usr@bank.com")

        res = client.get("/api/v1/users", headers=hdrs)
        assert res.status_code == 200
        ids = [u["id"] for u in res.json()["items"]]
        assert u_same.id in ids
        assert u_other.id not in ids

    def test_parts_returns_403(self, client, db):
        """client_user cannot access parts/warehouse."""
        cl = make_client(db, name="Parts Bank")
        hdrs = self._make_client_user_hdrs(db, cl.id, email="cu_parts@bank.com")

        res = client.get("/api/v1/parts", headers=hdrs)
        assert res.status_code == 403
        assert res.json()["error"] == "FORBIDDEN"

    def test_parts_get_by_id_returns_403(self, client, db):
        """client_user cannot access individual part."""
        cl = make_client(db, name="Parts Bank 2")
        part = make_spare_part(db, sku="SKU-CU-001")
        hdrs = self._make_client_user_hdrs(db, cl.id, email="cu_part2@bank.com")

        res = client.get(f"/api/v1/parts/{part.id}", headers=hdrs)
        assert res.status_code == 403
