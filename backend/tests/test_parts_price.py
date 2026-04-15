"""
Тесты для управления ценами матценностей (UC-102, BR-F-121, BR-F-122).
"""
from decimal import Decimal

from tests.conftest import (
    make_admin, make_svc_mgr, make_engineer, make_spare_part,
    auth_headers, make_user,
)


class TestHasPriceFilter:
    """GET /api/v1/parts?has_price=true — возвращать только позиции с unit_price > 0."""

    def test_has_price_false_by_default(self, client, db):
        admin = make_admin(db)
        make_spare_part(db, sku="P-001", quantity=5)   # price=100 из фабрики
        p0 = make_spare_part(db, sku="P-002", quantity=3)
        p0.unit_price = Decimal("0")
        db.commit()

        resp = client.get("/api/v1/parts", headers=auth_headers(admin.id, admin.roles))
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert p0.id in ids  # без фильтра — оба видны

    def test_has_price_true_excludes_zero_price(self, client, db):
        admin = make_admin(db)
        priced = make_spare_part(db, sku="P-003", quantity=5)  # price=100
        no_price = make_spare_part(db, sku="P-004", quantity=3)
        no_price.unit_price = Decimal("0")
        db.commit()

        resp = client.get(
            "/api/v1/parts",
            params={"has_price": True},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert priced.id in ids
        assert no_price.id not in ids

    def test_has_price_true_includes_nonzero(self, client, db):
        admin = make_admin(db)
        p = make_spare_part(db, sku="P-005", quantity=1)  # unit_price=100.00 из фабрики

        resp = client.get(
            "/api/v1/parts",
            params={"has_price": True},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert p.id in ids


class TestSetPartPrice:
    """PATCH /api/v1/parts/{id}/price — установить/изменить цену матценности."""

    def test_admin_can_set_price(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-001", quantity=5)
        part.unit_price = Decimal("0")
        db.commit()

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "1500.00", "currency": "RUB", "reason": "Первичная установка цены"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(str(data["unit_price"])) == Decimal("1500.00")
        assert data["currency"] == "RUB"

    def test_svc_mgr_can_set_price(self, client, db):
        mgr = make_svc_mgr(db)
        part = make_spare_part(db, sku="X-002", quantity=5)
        part.unit_price = Decimal("0")
        db.commit()

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "900.00", "currency": "RUB", "reason": "Плановое обновление цены"},
            headers=auth_headers(mgr.id, mgr.roles),
        )
        assert resp.status_code == 200

    def test_engineer_cannot_set_price(self, client, db):
        eng = make_engineer(db)
        part = make_spare_part(db, sku="X-003", quantity=5)

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "500.00", "currency": "RUB", "reason": "Попытка без прав"},
            headers=auth_headers(eng.id, eng.roles),
        )
        assert resp.status_code == 403

    def test_negative_price_rejected(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-004", quantity=5)

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "-10.00", "currency": "RUB", "reason": "Ошибочная цена негативная"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 422

    def test_short_reason_rejected(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-005", quantity=5)

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "100.00", "currency": "RUB", "reason": "ab"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 422

    def test_set_price_creates_history_record(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-006", quantity=5)
        old_price = Decimal(str(part.unit_price))  # 100.00 из фабрики

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "2000.00", "currency": "RUB", "reason": "Обновление прайса поставщика"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200

        # Проверяем историю
        hist_resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert hist_resp.status_code == 200
        history = hist_resp.json()
        assert len(history) == 1
        assert Decimal(str(history[0]["old_price"])) == old_price
        assert Decimal(str(history[0]["new_price"])) == Decimal("2000.00")
        assert history[0]["reason"] == "Обновление прайса поставщика"
        assert history[0]["changed_by"] == admin.id

    def test_part_not_found_returns_404(self, client, db):
        admin = make_admin(db)
        resp = client.patch(
            "/api/v1/parts/99999/price",
            json={"new_price": "100.00", "currency": "RUB", "reason": "Тест не найдено"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 404


class TestPriceHistory:
    """GET /api/v1/parts/{id}/price-history — получить историю цен."""

    def test_empty_history(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="H-001", quantity=5)

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_sorted_newest_first(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="H-002", quantity=5)
        part.unit_price = Decimal("0")
        db.commit()

        # Первая установка
        client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "100.00", "currency": "RUB", "reason": "Первая установка цены"},
            headers=auth_headers(admin.id, admin.roles),
        )
        # Вторая установка
        client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "200.00", "currency": "RUB", "reason": "Повторная установка цены"},
            headers=auth_headers(admin.id, admin.roles),
        )

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 2
        # Новейшая запись первая
        assert Decimal(str(history[0]["new_price"])) == Decimal("200.00")
        assert Decimal(str(history[1]["new_price"])) == Decimal("100.00")

    def test_engineer_can_view_history(self, client, db):
        eng = make_engineer(db)
        part = make_spare_part(db, sku="H-003", quantity=5)

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(eng.id, eng.roles),
        )
        assert resp.status_code == 200

    def test_client_user_cannot_view_history(self, client, db):
        cu = make_user(db, email="cu@test.com", roles=["client_user"])
        part = make_spare_part(db, sku="H-004", quantity=5)

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(cu.id, cu.roles),
        )
        assert resp.status_code == 403
