"""
Unit tests — /api/v1/notifications
Covers: настройки, нельзя отключить in_app (BR-F-1400),
список уведомлений, счётчик непрочитанных, отметка прочитанных.
"""
import pytest
from app.models import Notification, NotificationSetting
from tests.conftest import make_admin, make_engineer, make_user, auth_headers


def _admin(db):
    u = make_admin(db)
    return u, auth_headers(u.id, u.roles)


def _eng(db):
    u = make_engineer(db)
    return u, auth_headers(u.id, u.roles)


def _create_notification(db, user_id, is_read=False, event_type="ticket_assigned_to_me"):
    n = Notification(
        user_id=user_id,
        event_type=event_type,
        title="Test notification",
        body="Test body",
        is_read=is_read,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def _create_setting(db, user_id, event_type, channel, enabled=True):
    s = NotificationSetting(
        user_id=user_id,
        event_type=event_type,
        channel=channel,
        enabled=enabled,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


class TestNotificationSettings:
    def test_get_settings(self, client, db):
        u, hdrs = _admin(db)
        _create_setting(db, u.id, "ticket_assigned_to_me", "email")
        res = client.get("/api/v1/notifications/settings", headers=hdrs)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_enable_email_notification(self, client, db):
        u, hdrs = _admin(db)
        _create_setting(db, u.id, "ticket_status_changed", "email", enabled=False)
        res = client.put("/api/v1/notifications/settings", headers=hdrs, json={
            "event_type": "ticket_status_changed",
            "channel": "email",
            "enabled": True,
        })
        assert res.status_code == 200

    def test_disable_email_allowed(self, client, db):
        u, hdrs = _admin(db)
        _create_setting(db, u.id, "sla_warning", "email", enabled=True)
        res = client.put("/api/v1/notifications/settings", headers=hdrs, json={
            "event_type": "sla_warning",
            "channel": "email",
            "enabled": False,
        })
        assert res.status_code == 200

    def test_cannot_disable_in_app(self, client, db):
        """BR-F-1400: in_app channel cannot be disabled."""
        u, hdrs = _admin(db)
        _create_setting(db, u.id, "ticket_assigned_to_me", "in_app", enabled=True)
        res = client.put("/api/v1/notifications/settings", headers=hdrs, json={
            "event_type": "ticket_assigned_to_me",
            "channel": "in_app",
            "enabled": False,
        })
        assert res.status_code == 400
        assert res.json()["error"] == "CANNOT_DISABLE_IN_APP"

    def test_can_enable_in_app(self, client, db):
        """Enabling in_app is always allowed."""
        u, hdrs = _admin(db)
        _create_setting(db, u.id, "ticket_assigned_to_me", "in_app", enabled=True)
        res = client.put("/api/v1/notifications/settings", headers=hdrs, json={
            "event_type": "ticket_assigned_to_me",
            "channel": "in_app",
            "enabled": True,
        })
        assert res.status_code == 200

    def test_reset_settings(self, client, db):
        u, hdrs = _admin(db)
        res = client.post("/api/v1/notifications/settings/reset?confirm=true", headers=hdrs)
        assert res.status_code in (200, 204)

    def test_unauthenticated_blocked(self, client, db):
        res = client.get("/api/v1/notifications/settings")
        assert res.status_code == 401


class TestNotificationsList:
    def test_list_notifications(self, client, db):
        u, hdrs = _admin(db)
        _create_notification(db, u.id)
        res = client.get("/api/v1/notifications", headers=hdrs)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data

    def test_filter_unread(self, client, db):
        u, hdrs = _admin(db)
        _create_notification(db, u.id, is_read=False)
        _create_notification(db, u.id, is_read=True)
        res = client.get("/api/v1/notifications", headers=hdrs, params={"is_read": False})
        assert res.status_code == 200
        for n in res.json()["items"]:
            assert n["is_read"] is False

    def test_user_sees_only_own_notifications(self, client, db):
        u1, hdrs1 = _admin(db)
        u2 = make_user(db, email="other@t.com", roles=["engineer"])
        _create_notification(db, u1.id)
        _create_notification(db, u2.id)
        res = client.get("/api/v1/notifications", headers=hdrs1)
        for n in res.json()["items"]:
            assert n["user_id"] == u1.id


class TestUnreadCount:
    def test_unread_count_zero_initially(self, client, db):
        _, hdrs = _admin(db)
        res = client.get("/api/v1/notifications/unread-count", headers=hdrs)
        assert res.status_code == 200
        count = res.json().get("count", res.json().get("unread_count", -1))
        assert count == 0

    def test_unread_count_increments(self, client, db):
        u, hdrs = _admin(db)
        _create_notification(db, u.id, is_read=False)
        _create_notification(db, u.id, is_read=False)
        res = client.get("/api/v1/notifications/unread-count", headers=hdrs)
        count = res.json().get("count", res.json().get("unread_count", -1))
        assert count == 2

    def test_read_notification_not_counted(self, client, db):
        u, hdrs = _admin(db)
        _create_notification(db, u.id, is_read=True)
        res = client.get("/api/v1/notifications/unread-count", headers=hdrs)
        count = res.json().get("count", res.json().get("unread_count", -1))
        assert count == 0


class TestMarkRead:
    def test_mark_single_as_read(self, client, db):
        u, hdrs = _admin(db)
        n = _create_notification(db, u.id, is_read=False)
        res = client.post(f"/api/v1/notifications/{n.id}/read", headers=hdrs)
        assert res.status_code in (200, 204)
        db.refresh(n)
        assert n.is_read is True

    def test_mark_all_as_read(self, client, db):
        u, hdrs = _admin(db)
        _create_notification(db, u.id, is_read=False)
        _create_notification(db, u.id, is_read=False)
        res = client.post("/api/v1/notifications/read-all", headers=hdrs)
        assert res.status_code in (200, 204)
        count_res = client.get("/api/v1/notifications/unread-count", headers=hdrs)
        count = count_res.json().get("count", count_res.json().get("unread_count", -1))
        assert count == 0

    def test_cannot_mark_others_notification(self, client, db):
        u1, _ = _admin(db)
        u2 = make_user(db, email="other@t.com", roles=["engineer"])
        n = _create_notification(db, u1.id, is_read=False)
        eng_hdrs = auth_headers(u2.id, u2.roles)
        res = client.post(f"/api/v1/notifications/{n.id}/read", headers=eng_hdrs)
        # either 403 or 404 (notification not found for this user)
        assert res.status_code in (403, 404)
