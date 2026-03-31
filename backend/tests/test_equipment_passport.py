"""
UC-1001: Паспорт оборудования — тесты приёмочных критериев.

Покрывает Acceptance Criteria из UC-1001.md:
  AC-1: Успешное создание паспорта (все поля сохранены)
  AC-2: warranty_status вычисляется автоматически (on_warranty / expiring / expired)
  AC-3: Блокировка дубликата серийного номера (409, сообщение с именем клиента)
  AC-4: Редактирование паспорта (поля обновляются, warranty_status пересчитывается)
  AC-5: Статус «transferred» принимается системой
  AC-6: Новые поля (manufacture_date, sale_date, warranty_start, firmware_version) сохраняются и возвращаются
  AC-7: RBAC — engineer не может создать/изменить паспорт
"""
from datetime import date, timedelta
import pytest
from tests.conftest import (
    make_admin, make_engineer, make_user,
    make_client, make_equipment_model, make_equipment,
    auth_headers,
)

TODAY = date.today()


def _admin_headers(db):
    u = make_admin(db, email="eq_admin@test.com")
    return auth_headers(u.id, u.roles)


def _svc_headers(db):
    u = make_user(db, email="eq_svc@test.com", roles=["svc_mgr"])
    return auth_headers(u.id, u.roles)


def _eng_headers(db):
    u = make_engineer(db, email="eq_eng@test.com")
    return auth_headers(u.id, u.roles)


def _base_payload(client_id, model_id, serial="SN-PASSPORT-001"):
    return {
        "client_id": client_id,
        "model_id": model_id,
        "serial_number": serial,
        "location": "ул. Банковская, 1, Москва",
    }


# ── AC-1: Успешное создание паспорта ─────────────────────────────────────────

class TestCreatePassport:
    def test_create_minimal(self, client, db):
        """Паспорт создаётся с обязательными полями; статус = active."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Альфа")
        model = make_equipment_model(db, "Matica XID 580i")
        res = client.post("/api/v1/equipment", headers=hdrs, json=_base_payload(cl.id, model.id))
        assert res.status_code == 201
        body = res.json()
        assert body["serial_number"] == "SN-PASSPORT-001"
        assert body["status"] == "active"

    def test_create_full_passport(self, client, db):
        """Все поля UC-1001 сохраняются и возвращаются корректно (AC-6)."""
        hdrs = _svc_headers(db)
        cl = make_client(db, name="Банк Бета")
        model = make_equipment_model(db, "NCR 6683")
        warranty_end = (TODAY + timedelta(days=200)).isoformat()
        warranty_start = TODAY.isoformat()
        payload = {
            "client_id": cl.id,
            "model_id": model.id,
            "serial_number": "SN-FULL-001",
            "location": "пр. Ленина, 5",
            "manufacture_date": "2024-01-15",
            "sale_date": "2025-03-01",
            "warranty_start": warranty_start,
            "warranty_until": warranty_end,
            "firmware_version": "v3.14.159",
            "notes": "Новый аппарат",
        }
        res = client.post("/api/v1/equipment", headers=hdrs, json=payload)
        assert res.status_code == 201
        body = res.json()
        assert body["manufacture_date"] == "2024-01-15"
        assert body["sale_date"] == "2025-03-01"
        assert body["warranty_start"] == warranty_start
        assert body["firmware_version"] == "v3.14.159"

    def test_svc_mgr_can_create(self, client, db):
        """Роль svc_mgr имеет право создавать паспорта."""
        hdrs = _svc_headers(db)
        cl = make_client(db, name="Банк Гамма")
        model = make_equipment_model(db, "Diebold 522")
        res = client.post("/api/v1/equipment", headers=hdrs,
                          json=_base_payload(cl.id, model.id, "SN-SVC-001"))
        assert res.status_code == 201


# ── AC-2: warranty_status вычисляется автоматически ──────────────────────────

class TestWarrantyStatus:
    def test_on_warranty_more_than_30_days(self, client, db):
        """warranty_end > 30 дней → warranty_status = on_warranty."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Д")
        model = make_equipment_model(db, "Model W1")
        far_future = (TODAY + timedelta(days=200)).isoformat()
        res = client.post("/api/v1/equipment", headers=hdrs, json={
            **_base_payload(cl.id, model.id, "SN-WARR-ON"),
            "warranty_until": far_future,
        })
        assert res.status_code == 201
        assert res.json()["warranty_status"] == "on_warranty"

    def test_expiring_within_30_days(self, client, db):
        """warranty_end ≤ 30 дней → warranty_status = expiring."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Е")
        model = make_equipment_model(db, "Model W2")
        soon = (TODAY + timedelta(days=15)).isoformat()
        res = client.post("/api/v1/equipment", headers=hdrs, json={
            **_base_payload(cl.id, model.id, "SN-WARR-EXP"),
            "warranty_until": soon,
        })
        assert res.status_code == 201
        assert res.json()["warranty_status"] == "expiring"

    def test_expired_warranty(self, client, db):
        """warranty_end в прошлом → warranty_status = expired."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Ж")
        model = make_equipment_model(db, "Model W3")
        past = (TODAY - timedelta(days=10)).isoformat()
        res = client.post("/api/v1/equipment", headers=hdrs, json={
            **_base_payload(cl.id, model.id, "SN-WARR-PAST"),
            "warranty_until": past,
        })
        assert res.status_code == 201
        assert res.json()["warranty_status"] == "expired"

    def test_no_warranty_unknown(self, client, db):
        """warranty_end не указан → warranty_status = unknown."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк З")
        model = make_equipment_model(db, "Model W4")
        res = client.post("/api/v1/equipment", headers=hdrs,
                          json=_base_payload(cl.id, model.id, "SN-WARR-NONE"))
        assert res.status_code == 201
        assert res.json()["warranty_status"] == "unknown"


# ── AC-3: Блокировка дубликата серийного номера (BR-R-008) ───────────────────

class TestDuplicateSerial:
    def test_duplicate_returns_409(self, client, db):
        """Второй паспорт с тем же серийным номером возвращает 409."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Theta")
        model = make_equipment_model(db, "Model Dup")
        payload = _base_payload(cl.id, model.id, "SN-DUP-12345")
        client.post("/api/v1/equipment", headers=hdrs, json=payload)
        res = client.post("/api/v1/equipment", headers=hdrs, json=payload)
        assert res.status_code == 409

    def test_duplicate_message_includes_client_name(self, client, db):
        """Сообщение об ошибке содержит имя клиента-владельца (BR-R-008)."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Бета")
        model = make_equipment_model(db, "Model Dup2")
        sn = "SN-DUP-99999"
        client.post("/api/v1/equipment", headers=hdrs,
                    json=_base_payload(cl.id, model.id, sn))
        cl2 = make_client(db, name="Банк Гамма")
        res = client.post("/api/v1/equipment", headers=hdrs,
                          json=_base_payload(cl2.id, model.id, sn))
        assert res.status_code == 409
        detail = res.json()
        # message должно содержать имя клиента первого владельца
        assert "Банк Бета" in str(detail)


# ── AC-4: Редактирование паспорта ────────────────────────────────────────────

class TestEditPassport:
    def test_update_location(self, client, db):
        """Адрес установки обновляется."""
        hdrs = _admin_headers(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="SN-UPD-001")
        res = client.put(f"/api/v1/equipment/{eq.id}", headers=hdrs,
                         json={"location": "Новый адрес 999"})
        assert res.status_code == 200
        assert res.json()["location"] == "Новый адрес 999"

    def test_update_warranty_status_recalculated(self, client, db):
        """После обновления warranty_until warranty_status пересчитывается."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Рекалк")
        model = make_equipment_model(db, "Model Recalc")
        # создаём с истёкшей гарантией
        eq = make_equipment(db, cl.id, model.id, serial="SN-RECALC-001")
        eq.warranty_until = TODAY - timedelta(days=5)
        db.commit()

        get_res = client.get(f"/api/v1/equipment/{eq.id}", headers=hdrs)
        assert get_res.json()["warranty_status"] == "expired"

        # обновляем на будущую дату
        future = (TODAY + timedelta(days=100)).isoformat()
        put_res = client.put(f"/api/v1/equipment/{eq.id}", headers=hdrs,
                             json={"warranty_until": future})
        assert put_res.json()["warranty_status"] == "on_warranty"

    def test_update_new_passport_fields(self, client, db):
        """Поля manufacture_date, sale_date, warranty_start, firmware_version обновляются."""
        hdrs = _svc_headers(db)
        cl = make_client(db, name="Банк Иота")
        model = make_equipment_model(db, "Model Update")
        eq = make_equipment(db, cl.id, model.id, serial="SN-NEWF-001")
        res = client.put(f"/api/v1/equipment/{eq.id}", headers=hdrs, json={
            "manufacture_date": "2023-06-01",
            "sale_date": "2024-02-15",
            "warranty_start": "2024-02-15",
            "firmware_version": "v2.0.0",
        })
        assert res.status_code == 200
        body = res.json()
        assert body["manufacture_date"] == "2023-06-01"
        assert body["sale_date"] == "2024-02-15"
        assert body["warranty_start"] == "2024-02-15"
        assert body["firmware_version"] == "v2.0.0"


# ── AC-5: Статус «transferred» ────────────────────────────────────────────────

class TestTransferredStatus:
    def test_create_with_transferred_status(self, client, db):
        """Статус 'transferred' принимается при создании паспорта."""
        hdrs = _admin_headers(db)
        cl = make_client(db, name="Банк Кappa")
        model = make_equipment_model(db, "Model T1")
        res = client.post("/api/v1/equipment", headers=hdrs, json={
            **_base_payload(cl.id, model.id, "SN-TRANS-001"),
            "status": "transferred",
        })
        assert res.status_code == 201
        assert res.json()["status"] == "transferred"

    def test_update_to_transferred(self, client, db):
        """Можно изменить статус на 'transferred'."""
        hdrs = _svc_headers(db)
        cl = make_client(db, name="Банк Lambda")
        model = make_equipment_model(db, "Model T2")
        eq = make_equipment(db, cl.id, model.id, serial="SN-TRANS-002")
        res = client.put(f"/api/v1/equipment/{eq.id}", headers=hdrs,
                         json={"status": "transferred"})
        assert res.status_code == 200
        assert res.json()["status"] == "transferred"


# ── AC-7: RBAC ───────────────────────────────────────────────────────────────

class TestPassportRBAC:
    def test_engineer_cannot_create(self, client, db):
        """Engineer не может создать паспорт."""
        hdrs = _eng_headers(db)
        cl = make_client(db, name="Банк Mu")
        model = make_equipment_model(db, "Model RBAC")
        res = client.post("/api/v1/equipment", headers=hdrs,
                          json=_base_payload(cl.id, model.id, "SN-RBAC-001"))
        assert res.status_code == 403

    def test_engineer_cannot_update(self, client, db):
        """Engineer не может редактировать паспорт."""
        adm = _admin_headers(db)
        eng = _eng_headers(db)
        cl = make_client(db, name="Банк Nu")
        model = make_equipment_model(db, "Model RBAC2")
        eq = make_equipment(db, cl.id, model.id, serial="SN-RBAC-002")
        res = client.put(f"/api/v1/equipment/{eq.id}", headers=eng,
                         json={"location": "Hack"})
        assert res.status_code == 403

    def test_engineer_can_read(self, client, db):
        """Engineer может читать паспорт."""
        adm = _admin_headers(db)
        eng = _eng_headers(db)
        cl = make_client(db, name="Банк Xi")
        model = make_equipment_model(db, "Model RBAC3")
        eq = make_equipment(db, cl.id, model.id, serial="SN-RBAC-003")
        res = client.get(f"/api/v1/equipment/{eq.id}", headers=eng)
        assert res.status_code == 200
