"""
Tests for BR-F-125: ticket reopen (closed/completed → in_progress).

Covered:
- admin/svc_mgr/client_user can reopen from closed
- admin/svc_mgr/client_user can reopen from completed
- engineer CANNOT reopen from closed or completed
- closed_at is cleared on reopen
- status history records the transition with comment
- transition from cancelled → in_progress is still forbidden
"""
import pytest
from tests.conftest import (
    make_admin, make_svc_mgr, make_engineer, make_client,
    make_client_user, make_equipment_model, make_equipment, auth_headers,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _setup(db):
    """Create admin, svc_mgr, engineer, client_user, client, equipment.
    Returns (admin_hdrs, svc_hdrs, eng_hdrs, cu_hdrs, client_obj, eq)
    """
    admin = make_admin(db)
    svc = make_svc_mgr(db, email="svc2@t.com")
    eng = make_engineer(db, email="eng2@t.com")
    cl = make_client(db)
    cu = make_client_user(db, client_id=cl.id)
    model = make_equipment_model(db)
    eq = make_equipment(db, cl.id, model.id)
    return (
        auth_headers(admin.id, admin.roles),
        auth_headers(svc.id, svc.roles),
        auth_headers(eng.id, eng.roles),
        auth_headers(cu.id, cu.roles),
        cl, eq,
    )


def _create_ticket(http, headers, client_id, eq_id):
    r = http.post("/api/v1/tickets", headers=headers, json={
        "client_id": client_id,
        "equipment_id": eq_id,
        "title": "Reopen test",
        "type": "repair",
        "priority": "medium",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _change_status(http, ticket_id, new_status, headers, comment=None):
    payload = {"status": new_status}
    if comment:
        payload["comment"] = comment
    r = http.post(f"/api/v1/tickets/{ticket_id}/status", json=payload, headers=headers)
    return r


def _advance_to(http, ticket_id, target_status, admin_hdrs, eng):
    """Drive ticket through: new → assigned → in_progress → ... → target_status"""
    http.post(f"/api/v1/tickets/{ticket_id}/assign",
              json={"engineer_id": eng.id}, headers=admin_hdrs)
    path = {
        "in_progress": ["in_progress"],
        "completed":   ["in_progress", "completed"],
        "closed":      ["in_progress", "completed", "closed"],
        "cancelled":   ["cancelled"],
    }
    for s in path[target_status]:
        r = _change_status(http, ticket_id, s, admin_hdrs)
        assert r.status_code == 200, f"failed to reach {s}: {r.text}"


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def setup(client, db):
    admin_hdrs, svc_hdrs, eng_hdrs, cu_hdrs, cl, eq = _setup(db)
    # need raw engineer obj for assign
    from tests.conftest import make_engineer as _me
    eng = db.query(__import__("app.models", fromlist=["User"]).User)\
             .filter_by(email="eng2@t.com").first()
    return {
        "http": client,
        "admin": admin_hdrs,
        "svc": svc_hdrs,
        "eng": eng_hdrs,
        "cu": cu_hdrs,
        "cl": cl,
        "eq": eq,
        "eng_obj": eng,
    }


# ─── closed → in_progress ─────────────────────────────────────────────────────

class TestReopenFromClosed:
    def test_admin_can_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "closed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["admin"])
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_svc_mgr_can_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "closed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["svc"])
        assert r.status_code == 200

    def test_client_user_can_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "closed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["cu"])
        assert r.status_code == 200

    def test_engineer_cannot_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "closed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["eng"])
        assert r.status_code == 403
        assert r.json()["error"] == "FORBIDDEN"

    def test_closed_at_cleared_on_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "closed", s["admin"], s["eng_obj"])
        # closed_at должен быть заполнен после закрытия
        r_closed = s["http"].get(f"/api/v1/tickets/{tid}", headers=s["admin"])
        assert r_closed.json()["closed_at"] is not None
        # после возобновления — сброшен
        _change_status(s["http"], tid, "in_progress", s["admin"])
        r_open = s["http"].get(f"/api/v1/tickets/{tid}", headers=s["admin"])
        assert r_open.json()["closed_at"] is None

    def test_reopen_recorded_in_history(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "closed", s["admin"], s["eng_obj"])
        _change_status(s["http"], tid, "in_progress", s["admin"], comment="Повторное обращение")
        r = s["http"].get(f"/api/v1/tickets/{tid}/status-history", headers=s["admin"])
        assert r.status_code == 200
        last = r.json()[-1]
        assert last["from_status"] == "closed"
        assert last["to_status"] == "in_progress"
        assert last["comment"] == "Повторное обращение"


# ─── completed → in_progress ──────────────────────────────────────────────────

class TestReopenFromCompleted:
    def test_admin_can_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "completed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["admin"])
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_svc_mgr_can_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "completed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["svc"])
        assert r.status_code == 200

    def test_engineer_cannot_reopen(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _advance_to(s["http"], tid, "completed", s["admin"], s["eng_obj"])
        r = _change_status(s["http"], tid, "in_progress", s["eng"])
        assert r.status_code == 403
        assert r.json()["error"] == "FORBIDDEN"


# ─── forbidden transitions ────────────────────────────────────────────────────

class TestForbiddenTransitions:
    def test_cannot_reopen_cancelled(self, setup):
        s = setup
        tid = _create_ticket(s["http"], s["admin"], s["cl"].id, s["eq"].id)
        _change_status(s["http"], tid, "cancelled", s["admin"])
        r = _change_status(s["http"], tid, "in_progress", s["admin"])
        assert r.status_code == 400
        assert r.json()["error"] == "BR_VIOLATION"
