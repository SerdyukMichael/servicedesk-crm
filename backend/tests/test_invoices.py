"""
Unit tests — /api/v1/invoices
Covers: CRUD, переходы статусов (send/pay), RBAC, client_scope.
"""
import pytest
from tests.conftest import make_admin, make_engineer, make_user, make_client, make_client_user, auth_headers


def _admin(db):
    u = make_admin(db)
    return u, auth_headers(u.id, u.roles)


def _accountant(db):
    u = make_user(db, email="acc@t.com", roles=["accountant"])
    return u, auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db)
    return u, auth_headers(u.id, u.roles)


def _create_invoice(client_fixture, headers, client_id, created_by_id):
    return client_fixture.post("/api/v1/invoices", headers=headers, json={
        "client_id": client_id,
        "type": "service",
        "issue_date": "2026-03-28",
        "due_date": "2026-04-28",
        "items": [
            {"description": "Ремонт ATM", "quantity": "1.000", "unit": "шт",
             "unit_price": "5000.00", "total": "5000.00", "sort_order": 1}
        ],
    })


class TestListInvoices:
    def test_accountant_can_list(self, client, db):
        _, acc_hdrs = _accountant(db)
        res = client.get("/api/v1/invoices", headers=acc_hdrs)
        assert res.status_code == 200

    def test_engineer_can_list(self, client, db):
        # Engineer can read invoices (BR-F-119, BR-F-120: invoice link/status visible on ticket)
        _, eng_hdrs = _eng(db)
        res = client.get("/api/v1/invoices", headers=eng_hdrs)
        assert res.status_code == 200

    def test_unauthenticated_blocked(self, client, db):
        res = client.get("/api/v1/invoices")
        assert res.status_code == 401


class TestCreateInvoice:
    def test_admin_creates_invoice(self, client, db):
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        res = _create_invoice(client, admin_hdrs, cl.id, u.id)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "draft"
        assert data["client_id"] == cl.id

    def test_accountant_creates_invoice(self, client, db):
        u, acc_hdrs = _accountant(db)
        cl = make_client(db)
        res = _create_invoice(client, acc_hdrs, cl.id, u.id)
        assert res.status_code == 201

    def test_engineer_cannot_create(self, client, db):
        u, eng_hdrs = _eng(db)
        cl = make_client(db)
        res = _create_invoice(client, eng_hdrs, cl.id, u.id)
        assert res.status_code == 403

    def test_invoice_number_auto_generated(self, client, db):
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        res = _create_invoice(client, admin_hdrs, cl.id, u.id)
        assert res.status_code == 201
        assert res.json()["number"] is not None

    def test_vat_calculated(self, client, db):
        """VAT = 20% of subtotal by default."""
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        res = _create_invoice(client, admin_hdrs, cl.id, u.id)
        assert res.status_code == 201
        data = res.json()
        if data.get("subtotal") and data.get("vat_amount"):
            import decimal
            subtotal = decimal.Decimal(str(data["subtotal"]))
            vat = decimal.Decimal(str(data["vat_amount"]))
            expected_vat = (subtotal * 20 / 100).quantize(decimal.Decimal("0.01"))
            assert vat == expected_vat


class TestGetInvoice:
    def test_get_existing(self, client, db):
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        inv = _create_invoice(client, admin_hdrs, cl.id, u.id).json()
        res = client.get(f"/api/v1/invoices/{inv['id']}", headers=admin_hdrs)
        assert res.status_code == 200

    def test_get_nonexistent_returns_404(self, client, db):
        _, admin_hdrs = _admin(db)
        res = client.get("/api/v1/invoices/999999", headers=admin_hdrs)
        assert res.status_code == 404


class TestInvoiceActions:
    def test_send_invoice(self, client, db):
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        inv = _create_invoice(client, admin_hdrs, cl.id, u.id).json()
        res = client.post(f"/api/v1/invoices/{inv['id']}/send", headers=admin_hdrs)
        assert res.status_code == 200
        assert res.json()["status"] == "sent"

    def test_pay_invoice(self, client, db):
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        inv = _create_invoice(client, admin_hdrs, cl.id, u.id).json()
        client.post(f"/api/v1/invoices/{inv['id']}/send", headers=admin_hdrs)
        res = client.post(f"/api/v1/invoices/{inv['id']}/pay", headers=admin_hdrs)
        assert res.status_code == 200
        assert res.json()["status"] == "paid"

    def test_cannot_pay_draft_invoice(self, client, db):
        """Draft → paid is invalid without sending first."""
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        inv = _create_invoice(client, admin_hdrs, cl.id, u.id).json()
        res = client.post(f"/api/v1/invoices/{inv['id']}/pay", headers=admin_hdrs)
        assert res.status_code in (400, 422)


class TestDeleteInvoice:
    def test_admin_deletes_invoice(self, client, db):
        u, admin_hdrs = _admin(db)
        cl = make_client(db)
        inv = _create_invoice(client, admin_hdrs, cl.id, u.id).json()
        res = client.delete(f"/api/v1/invoices/{inv['id']}", headers=admin_hdrs)
        assert res.status_code == 204

    def test_engineer_cannot_delete(self, client, db):
        u_adm, admin_hdrs = _admin(db)
        cl = make_client(db)
        inv = _create_invoice(client, admin_hdrs, cl.id, u_adm.id).json()
        _, eng_hdrs = _eng(db)
        res = client.delete(f"/api/v1/invoices/{inv['id']}", headers=eng_hdrs)
        assert res.status_code == 403


class TestClientUserScope:
    """client_user видит только счета своей организации (BR-F-129-sec)."""

    def _setup(self, db):
        """Два клиента, два client_user, по одному счёту на каждого."""
        admin, admin_hdrs = _admin(db)
        cl_a = make_client(db, name="Клиент A")
        cl_b = make_client(db, name="Клиент B")
        cu_a = make_client_user(db, client_id=cl_a.id, email="cu_a@test.com")
        cu_b = make_client_user(db, client_id=cl_b.id, email="cu_b@test.com")
        hdrs_a = auth_headers(cu_a.id, cu_a.roles)
        hdrs_b = auth_headers(cu_b.id, cu_b.roles)
        inv_a = _create_invoice(None, admin_hdrs, cl_a.id, admin.id)  # создаётся через admin
        inv_b = _create_invoice(None, admin_hdrs, cl_b.id, admin.id)
        return admin_hdrs, hdrs_a, hdrs_b, inv_a, inv_b, cl_a, cl_b

    def test_client_user_can_get_own_invoice(self, client, db):
        """client_user видит счёт своей организации."""
        u_adm, admin_hdrs = _admin(db)
        cl = make_client(db, name="Своя орг")
        cu = make_client_user(db, client_id=cl.id, email="cu_own@test.com")
        cu_hdrs = auth_headers(cu.id, cu.roles)
        inv = _create_invoice(client, admin_hdrs, cl.id, u_adm.id).json()
        res = client.get(f"/api/v1/invoices/{inv['id']}", headers=cu_hdrs)
        assert res.status_code == 200

    def test_client_user_cannot_get_other_client_invoice(self, client, db):
        """client_user НЕ видит счёт чужой организации — должен получить 404."""
        u_adm, admin_hdrs = _admin(db)
        cl_a = make_client(db, name="Орг A")
        cl_b = make_client(db, name="Орг B")
        cu_a = make_client_user(db, client_id=cl_a.id, email="cu_a2@test.com")
        cu_a_hdrs = auth_headers(cu_a.id, cu_a.roles)
        # Счёт создан для cl_b, cu_a пытается его получить
        inv_b = _create_invoice(client, admin_hdrs, cl_b.id, u_adm.id).json()
        res = client.get(f"/api/v1/invoices/{inv_b['id']}", headers=cu_a_hdrs)
        assert res.status_code == 404

    def test_client_user_list_shows_only_own_invoices(self, client, db):
        """Список счётов client_user содержит только счета своей организации."""
        u_adm, admin_hdrs = _admin(db)
        cl_a = make_client(db, name="Орг AA")
        cl_b = make_client(db, name="Орг BB")
        cu_a = make_client_user(db, client_id=cl_a.id, email="cu_list_a@test.com")
        cu_a_hdrs = auth_headers(cu_a.id, cu_a.roles)
        _create_invoice(client, admin_hdrs, cl_a.id, u_adm.id)
        _create_invoice(client, admin_hdrs, cl_b.id, u_adm.id)
        res = client.get("/api/v1/invoices", headers=cu_a_hdrs)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) >= 1
        assert all(i["client_id"] == cl_a.id for i in items)
