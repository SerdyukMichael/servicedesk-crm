"""
Notifications and notification settings endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Notification, NotificationSetting, User
from app.api.deps import get_current_user
from app.schemas import (
    NotificationResponse, NotificationSettingResponse,
    NotificationSettingUpdate, PaginatedResponse,
)

router = APIRouter()

# Default event types for which settings are created
_DEFAULT_EVENTS = [
    "ticket_created",
    "ticket_assigned",
    "ticket_status_changed",
    "ticket_comment_added",
    "ticket_closed",
    "sla_warning",
    "sla_breach",
]
_DEFAULT_CHANNELS = ["email", "push", "in_app"]


def _ensure_settings(user: User, db: Session) -> None:
    """Create default notification settings for a user if they don't exist yet."""
    for event in _DEFAULT_EVENTS:
        for channel in _DEFAULT_CHANNELS:
            exists = (
                db.query(NotificationSetting)
                .filter(
                    NotificationSetting.user_id == user.id,
                    NotificationSetting.event_type == event,
                    NotificationSetting.channel == channel,
                )
                .first()
            )
            if not exists:
                db.add(
                    NotificationSetting(
                        user_id=user.id,
                        event_type=event,
                        channel=channel,
                        enabled=True,
                    )
                )
    db.commit()


# ─── Notifications ────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[NotificationResponse])
def list_notifications(
    is_read: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit, has_more=(skip + limit) < total)


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Уведомление не найдено"},
        )
    notif.is_read = True
    db.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()


# ─── Notification Settings ────────────────────────────────────────────────────

@router.get("/settings", response_model=list[NotificationSettingResponse])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_settings(current_user, db)
    return (
        db.query(NotificationSetting)
        .filter(NotificationSetting.user_id == current_user.id)
        .order_by(NotificationSetting.event_type, NotificationSetting.channel)
        .all()
    )


@router.put("/settings", response_model=NotificationSettingResponse)
def update_setting(
    data: NotificationSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.channel == "in_app" and not data.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "CANNOT_DISABLE_IN_APP", "message": "Нельзя отключить in_app уведомления"},
        )
    setting = (
        db.query(NotificationSetting)
        .filter(
            NotificationSetting.user_id == current_user.id,
            NotificationSetting.event_type == data.event_type,
            NotificationSetting.channel == data.channel,
        )
        .first()
    )
    if not setting:
        setting = NotificationSetting(
            user_id=current_user.id,
            event_type=data.event_type,
            channel=data.channel,
        )
        db.add(setting)
    setting.enabled = data.enabled
    db.commit()
    db.refresh(setting)
    return setting


@router.post("/settings/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).delete()
    db.commit()
    _ensure_settings(current_user, db)
