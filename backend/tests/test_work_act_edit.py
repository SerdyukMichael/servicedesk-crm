"""
TDD tests for work act editing (BR-F-114, BR-F-115).

BR-F-114: Act can be edited (description + items) until signed.
          Items are fully replaced (delete+insert).
BR-F-115: Editing a signed act returns 403.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from app.models import WorkAct, WorkActItem
from tests.conftest import (
    make_admin, make_engineer, admin_headers, auth_headers,
    make_client, make_equipment_model, make_equipment, make_ticket,
    make_spare_part, make_service_catalog_item,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_ticket_status(db, ticket_id, status):
    db.execute(text("UPDATE tickets SET status=:s WHERE id=:id"), {"s": status, "id": ticket_id})
    db.commit()


def _make_ticket_in_progress(db, cli, admin):
    model = make_equipment_model(db)
    equip = make_equipment(db, cli.id, model.id)
    ticket = make_ticket(db, cli.id, equip.id, admin.id)
    _set_ticket_status(db, ticket.id, "in_progress")
    return ticket


def _create_act(api_client, ticket_id, headers, description="Описание работ", items=None):
    """Create a work act via POST and return JSON response."""
    payload = {"work_description": description}
    if items:
        payload["items"] = items
    r = api_client.post(f"/api/v1/tickets/{ticket_id}/work-act", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _sign_act(db, act_id: int, signer_id: int):
    """Directly sign an act in DB to simulate signed state."""
    act = db.query(WorkAct).filter(WorkAct.id == act_id).first()
    act.signed_by = signer_id
    act.signed_at = datetime.utcnow()
    db.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestWorkActEdit:

    def test_patch_updates_description(self, client, db):
        """PATCH /tickets/{id}/work-act updates work_description."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        _create_act(client, ticket.id, headers, description="Старое описание")

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"work_description": "Новое описание"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["work_description"] == "Новое описание"

    def test_patch_replaces_items_fully(self, client, db):
        """PATCH replaces all items (old items deleted, new ones inserted)."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc1 = make_service_catalog_item(db, code="EDT-SRV-001", unit_price=1000.00)
        svc2 = make_service_catalog_item(db, code="EDT-SRV-002", unit_price=2000.00)

        _create_act(client, ticket.id, headers, items=[{
            "item_type": "service",
            "service_id": svc1.id,
            "name": "Услуга 1",
            "quantity": "1",
            "unit": "шт",
            "unit_price": "1000.00",
        }])

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"items": [{
                "item_type": "service",
                "service_id": svc2.id,
                "name": "Услуга 2",
                "quantity": "3",
                "unit": "шт",
                "unit_price": "2000.00",
            }]},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Услуга 2"
        assert data["items"][0]["total"] == "6000.00"

    def test_patch_removes_all_items_when_empty_list(self, client, db):
        """PATCH with items=[] removes all existing items."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="EDT-SRV-003", unit_price=500.00)

        _create_act(client, ticket.id, headers, items=[{
            "item_type": "service",
            "service_id": svc.id,
            "name": "Услуга",
            "quantity": "1",
            "unit": "шт",
            "unit_price": "500.00",
        }])

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"items": []},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_patch_returns_404_when_no_act(self, client, db):
        """PATCH on a ticket with no act returns 404."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"work_description": "test"},
            headers=headers,
        )
        assert r.status_code == 404

    def test_patch_signed_act_returns_403(self, client, db):
        """PATCH on a signed act returns 403 Forbidden (BR-F-115)."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        act_data = _create_act(client, ticket.id, headers)
        _sign_act(db, act_data["id"], admin.id)

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"work_description": "Попытка изменить подписанный акт"},
            headers=headers,
        )
        assert r.status_code == 403
        assert "подписан" in r.json()["message"].lower()

    def test_patch_unsigned_act_allowed(self, client, db):
        """PATCH on an unsigned act is allowed (BR-F-114)."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        _create_act(client, ticket.id, headers, description="Черновик")

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"work_description": "Финальное описание"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["work_description"] == "Финальное описание"

    def test_patch_preserves_unchanged_fields(self, client, db):
        """PATCH only changes provided fields, leaves others intact."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        _create_act(client, ticket.id, headers,
                    description="Описание",
                    items=[])

        # Update only total_time_minutes
        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"total_time_minutes": 90},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["work_description"] == "Описание"
        assert data["total_time_minutes"] == 90

    def test_patch_forbidden_for_unauthorized_role(self, client, db):
        """Clients (client_user role) cannot edit acts."""
        from app.models import User
        admin = make_admin(db)
        admin_h = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        _create_act(client, ticket.id, admin_h)

        # Create client_user
        cu = User(
            email="cu_edit@test.com",
            full_name="Client Portal User",
            password_hash="hashed",
            roles=["client_user"],
            client_id=cli.id,
            is_active=True,
            is_deleted=False,
        )
        db.add(cu)
        db.commit()
        db.refresh(cu)

        r = client.patch(
            f"/api/v1/tickets/{ticket.id}/work-act",
            json={"work_description": "Попытка"},
            headers=auth_headers(cu.id, cu.roles),
        )
        assert r.status_code == 403
