"""
UC-1002: История ремонтов оборудования — тесты приёмочных критериев.

Покрывает все AC из UC-1002.md:
  AC-1: 3 записи в хронологическом порядке (новые сверху)
  AC-2: Переход к карточке заявки (ticket_id / ticket_number в записи)
  AC-3: Пустая история — пустой массив (АП-2)
  AC-4: Фильтрация по типу работ (АП-1)
  AC-5: Раскрытие деталей: инженер, запчасти, описание
  BR-F-906: Авто-создание записи при переходе в статус completed
"""
from datetime import datetime, timedelta
import pytest
from app.models import RepairHistory, WorkAct
from tests.conftest import (
    make_admin, make_engineer, make_user,
    make_client, make_equipment_model, make_equipment, make_ticket,
    auth_headers,
)


def _adm(db):
    u = make_admin(db, email="rh_admin@t.com")
    return u, auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db, email="rh_eng@t.com")
    return u, auth_headers(u.id, u.roles)


def _make_repair_history(db, equipment_id, ticket_id=None,
                          action_type="unplanned_repair",
                          performed_at=None, description=None, parts_used=None):
    rh = RepairHistory(
        equipment_id=equipment_id,
        ticket_id=ticket_id,
        action_type=action_type,
        description=description or "Выполнен ремонт",
        performed_at=performed_at or datetime.utcnow(),
        parts_used=parts_used,
    )
    db.add(rh)
    db.commit()
    db.refresh(rh)
    return rh


def _set_ticket_status(client, ticket_id, status, headers, comment=None):
    payload = {"status": status}
    if comment:
        payload["comment"] = comment
    return client.patch(f"/api/v1/tickets/{ticket_id}/status",
                        headers=headers, json=payload)


# ── Шаги подготовки: перевести заявку в нужный статус ────────────────────────

def _advance_to_in_progress(client, ticket, engineer, adm_hdrs, eng_hdrs):
    """new → assigned → in_progress"""
    client.patch(f"/api/v1/tickets/{ticket.id}/assign",
                 headers=adm_hdrs, json={"engineer_id": engineer.id})
    client.patch(f"/api/v1/tickets/{ticket.id}/status",
                 headers=eng_hdrs, json={"status": "in_progress"})


# ── AC-3: Пустая история ─────────────────────────────────────────────────────

class TestEmptyHistory:
    def test_empty_history_returns_empty_list(self, client, db):
        """АП-2: нет заявок — возвращается пустой массив."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-EMPTY-001")
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        assert res.status_code == 200
        assert res.json() == []


# ── AC-1: Хронологический порядок (новые сверху) ─────────────────────────────

class TestHistoryOrder:
    def test_records_ordered_newest_first(self, client, db):
        """3 записи возвращаются от новой к старой (performed_at DESC)."""
        _, hdrs = _adm(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-ORDER-001")
        now = datetime.utcnow()
        _make_repair_history(db, eq.id, performed_at=now - timedelta(days=30))
        _make_repair_history(db, eq.id, performed_at=now - timedelta(days=10))
        _make_repair_history(db, eq.id, performed_at=now - timedelta(days=1))
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 3
        dates = [item["work_date"] for item in items]
        assert dates == sorted(dates, reverse=True), "Ожидается сортировка от новой к старой"

    def test_three_records_count(self, client, db):
        """Все 3 записи присутствуют в ответе."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-CNT-001")
        for i in range(3):
            _make_repair_history(db, eq.id)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        assert len(res.json()) == 3


# ── AC-2: Ссылка на заявку (ticket_id, ticket_number) ────────────────────────

class TestTicketLink:
    def test_history_contains_ticket_id_and_number(self, client, db):
        """Запись содержит ticket_id и ticket_number для перехода в карточку заявки."""
        admin, adm_hdrs = _adm(db)
        eng, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-LINK-001")
        ticket = make_ticket(db, cl.id, eq.id, admin.id)
        rh = _make_repair_history(db, eq.id, ticket_id=ticket.id)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        assert res.status_code == 200
        item = res.json()[0]
        assert item["ticket_id"] == ticket.id
        assert item["ticket_number"] == ticket.number

    def test_history_without_ticket(self, client, db):
        """Запись без заявки: ticket_id = null, ticket_number = null."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-NOLINK-001")
        _make_repair_history(db, eq.id, ticket_id=None)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        item = res.json()[0]
        assert item["ticket_id"] is None
        assert item["ticket_number"] is None


# ── AC-4: Фильтрация по типу работ (АП-1) ────────────────────────────────────

class TestFilterByWorkType:
    def test_filter_returns_only_matching_type(self, client, db):
        """Фильтр work_type возвращает только записи указанного типа."""
        _, hdrs = _adm(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-FILTER-001")
        _make_repair_history(db, eq.id, action_type="unplanned_repair")
        _make_repair_history(db, eq.id, action_type="unplanned_repair")
        _make_repair_history(db, eq.id, action_type="planned_maintenance")
        res = client.get(f"/api/v1/equipment/{eq.id}/history",
                         headers=hdrs, params={"work_type": "unplanned_repair"})
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 2
        assert all(i["work_type"] == "unplanned_repair" for i in items)

    def test_filter_no_match_returns_empty(self, client, db):
        """Фильтр без совпадений возвращает пустой массив."""
        _, hdrs = _adm(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-FILTER-002")
        _make_repair_history(db, eq.id, action_type="unplanned_repair")
        res = client.get(f"/api/v1/equipment/{eq.id}/history",
                         headers=hdrs, params={"work_type": "installation"})
        assert res.json() == []

    def test_filter_maintenance_one_result(self, client, db):
        """Из смешанной истории фильтр planned_maintenance возвращает 1 запись."""
        _, hdrs = _adm(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-FILTER-003")
        _make_repair_history(db, eq.id, action_type="unplanned_repair")
        _make_repair_history(db, eq.id, action_type="unplanned_repair")
        _make_repair_history(db, eq.id, action_type="planned_maintenance")
        res = client.get(f"/api/v1/equipment/{eq.id}/history",
                         headers=hdrs, params={"work_type": "planned_maintenance"})
        assert len(res.json()) == 1


# ── AC-5: Состав записи (инженер, запчасти, описание) ────────────────────────

class TestRecordDetails:
    def test_parts_used_returned(self, client, db):
        """Поле parts_used возвращается в составе записи."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-PARTS-001")
        parts = [{"part_id": 1, "name": "Картридж", "qty": 2}]
        _make_repair_history(db, eq.id, parts_used=parts)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        item = res.json()[0]
        assert item["parts_used"] == parts

    def test_description_returned(self, client, db):
        """Описание работ возвращается в составе записи."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-DESC-001")
        _make_repair_history(db, eq.id, description="Заменён картридж принтера")
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        assert res.json()[0]["description"] == "Заменён картридж принтера"

    def test_work_type_alias_present(self, client, db):
        """Поле work_type (алиас action_type) присутствует в ответе."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-ALIAS-001")
        _make_repair_history(db, eq.id, action_type="warranty_repair")
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        item = res.json()[0]
        assert item["work_type"] == "warranty_repair"
        assert item["action_type"] == "warranty_repair"

    def test_work_date_alias_present(self, client, db):
        """Поле work_date (алиас performed_at) присутствует в ответе."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-DATE-001")
        _make_repair_history(db, eq.id)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        item = res.json()[0]
        assert "work_date" in item
        assert item["work_date"] is not None


# ── BR-F-906: Автосоздание при завершении заявки ─────────────────────────────

class TestAutoCreateOnComplete:
    def test_repair_history_created_on_completed(self, client, db):
        """При переходе в статус 'completed' создаётся запись repair_history."""
        admin, adm_hdrs = _adm(db)
        eng, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-AUTO-001")
        ticket = make_ticket(db, cl.id, eq.id, admin.id, priority="medium")
        _advance_to_in_progress(client, ticket, eng, adm_hdrs, eng_hdrs)

        res_before = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        assert len(res_before.json()) == 0

        _set_ticket_status(client, ticket.id, "completed", eng_hdrs)

        res_after = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        assert len(res_after.json()) == 1
        entry = res_after.json()[0]
        assert entry["ticket_id"] == ticket.id
        assert entry["work_type"] == "unplanned_repair"  # ticket.type = "repair"

    def test_work_type_mapped_from_ticket_type(self, client, db):
        """work_type корректно маппится из ticket.type."""
        from app.models import Ticket as TicketModel
        admin, adm_hdrs = _adm(db)
        eng, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-MAP-001")
        ticket = make_ticket(db, cl.id, eq.id, admin.id)
        # Изменяем тип заявки на maintenance
        t = db.query(TicketModel).filter_by(id=ticket.id).first()
        t.type = "maintenance"
        db.commit()
        _advance_to_in_progress(client, ticket, eng, adm_hdrs, eng_hdrs)
        _set_ticket_status(client, ticket.id, "completed", eng_hdrs)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        assert res.json()[0]["work_type"] == "planned_maintenance"

    def test_no_duplicate_on_second_complete(self, client, db):
        """Повторный completed не создаёт вторую запись истории."""
        admin, adm_hdrs = _adm(db)
        eng, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-NODUP-001")
        ticket = make_ticket(db, cl.id, eq.id, admin.id)
        _advance_to_in_progress(client, ticket, eng, adm_hdrs, eng_hdrs)
        _set_ticket_status(client, ticket.id, "completed", eng_hdrs)
        # Переводим обратно в in_progress, затем снова в completed
        _set_ticket_status(client, ticket.id, "in_progress", eng_hdrs)
        _set_ticket_status(client, ticket.id, "completed", eng_hdrs)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        assert len(res.json()) == 1, "Не должно быть дубликатов"

    def test_no_history_if_no_equipment(self, client, db):
        """Заявка без оборудования не создаёт repair_history."""
        admin, adm_hdrs = _adm(db)
        eng, eng_hdrs = _eng(db)
        cl = make_client(db)
        ticket = make_ticket(db, cl.id, None, admin.id)  # equipment_id=None
        _advance_to_in_progress(client, ticket, eng, adm_hdrs, eng_hdrs)
        _set_ticket_status(client, ticket.id, "completed", eng_hdrs)
        # Проверяем что ни одной RepairHistory не создано
        from app.models import RepairHistory as RH
        count = db.query(RH).filter_by(ticket_id=ticket.id).count()
        assert count == 0

    def test_description_from_work_act(self, client, db):
        """Если есть акт, описание берётся из work_description акта."""
        admin, adm_hdrs = _adm(db)
        eng, eng_hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-ACT-001")
        ticket = make_ticket(db, cl.id, eq.id, admin.id)
        _advance_to_in_progress(client, ticket, eng, adm_hdrs, eng_hdrs)
        # Создаём акт выполненных работ
        act = WorkAct(
            ticket_id=ticket.id,
            engineer_id=eng.id,
            work_description="Выполнена замена термоголовки",
            parts_used=[{"part_id": 5, "name": "Термоголовка", "qty": 1}],
        )
        db.add(act)
        db.commit()
        _set_ticket_status(client, ticket.id, "completed", eng_hdrs)
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=eng_hdrs)
        entry = res.json()[0]
        assert entry["description"] == "Выполнена замена термоголовки"
        assert entry["parts_used"] == [{"part_id": 5, "name": "Термоголовка", "qty": 1}]


# ── RBAC: любой авторизованный читает историю ────────────────────────────────

class TestHistoryRBAC:
    def test_engineer_can_read_history(self, client, db):
        """Инженер может читать историю ремонтов."""
        _, hdrs = _eng(db)
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-RBAC-001")
        res = client.get(f"/api/v1/equipment/{eq.id}/history", headers=hdrs)
        assert res.status_code == 200

    def test_unauthenticated_denied(self, client, db):
        """Без токена — 401 / 403."""
        cl = make_client(db)
        model = make_equipment_model(db)
        eq = make_equipment(db, cl.id, model.id, serial="RH-RBAC-002")
        res = client.get(f"/api/v1/equipment/{eq.id}/history")
        assert res.status_code in (401, 403)
