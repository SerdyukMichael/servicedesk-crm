from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Notification, Ticket, User

FINAL_STATUSES = {"completed", "closed", "cancelled"}
REACTION_DONE_STATUSES = {"in_progress", "waiting_part", "on_review", "completed", "closed", "cancelled"}


@shared_task(name="app.tasks.sla.check_sla_deadlines")
def check_sla_deadlines():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        _check_reaction_breach(db, now)
        _check_resolution_breach(db, now)
        _check_reaction_warning(db, now)
        _check_resolution_warning(db, now)
        db.commit()
    finally:
        db.close()


def _svc_mgr_ids(db: Session) -> list[int]:
    users = db.query(User).filter(User.is_active.is_(True)).all()
    return [u.id for u in users if "svc_mgr" in (u.roles or [])]


def _add_notification(db: Session, user_ids: list[int], title: str, ticket_id: int, event_type: str):
    for uid in user_ids:
        db.add(Notification(
            user_id=uid,
            event_type=event_type,
            title=title,
            ticket_id=ticket_id,
        ))


def _check_reaction_breach(db: Session, now: datetime):
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.is_deleted.is_(False),
            Ticket.status.in_(("new", "assigned")),
            Ticket.sla_reaction_deadline.is_not(None),
            Ticket.sla_reaction_deadline < now,
            Ticket.sla_reaction_escalated_at.is_(None),
        )
        .all()
    )
    mgr_ids = _svc_mgr_ids(db) if tickets else []
    for t in tickets:
        t.sla_reaction_violated = True
        t.sla_reaction_escalated_at = now
        title = f"SLA реакции нарушен: заявка {t.number}"
        _add_notification(db, mgr_ids, title, t.id, "sla_breach_reaction")


def _check_resolution_breach(db: Session, now: datetime):
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.is_deleted.is_(False),
            ~Ticket.status.in_(FINAL_STATUSES),
            Ticket.sla_resolution_deadline.is_not(None),
            Ticket.sla_resolution_deadline < now,
            Ticket.sla_resolution_escalated_at.is_(None),
        )
        .all()
    )
    mgr_ids = _svc_mgr_ids(db) if tickets else []
    for t in tickets:
        t.sla_resolution_violated = True
        t.sla_resolution_escalated_at = now
        title = f"SLA решения нарушен: заявка {t.number}"
        _add_notification(db, mgr_ids, title, t.id, "sla_breach_resolution")
        if t.assigned_to and t.assigned_to not in mgr_ids:
            _add_notification(db, [t.assigned_to], title, t.id, "sla_breach_resolution")


def _check_reaction_warning(db: Session, now: datetime):
    warn_threshold = now + timedelta(hours=1)
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.is_deleted.is_(False),
            Ticket.status.in_(("new", "assigned")),
            Ticket.sla_reaction_deadline.is_not(None),
            Ticket.sla_reaction_deadline <= warn_threshold,
            Ticket.sla_reaction_deadline > now,
            Ticket.sla_reaction_violated.is_(False),
            Ticket.sla_reaction_escalated_at.is_(None),
        )
        .all()
    )
    if not tickets:
        return
    mgr_ids = _svc_mgr_ids(db)
    for t in tickets:
        title = f"⚠️ SLA реакции — 1 час: заявка {t.number}"
        _add_notification(db, mgr_ids, title, t.id, "sla_warning_reaction")


def _check_resolution_warning(db: Session, now: datetime):
    warn_threshold = now + timedelta(hours=4)
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.is_deleted.is_(False),
            ~Ticket.status.in_(FINAL_STATUSES),
            Ticket.sla_resolution_deadline.is_not(None),
            Ticket.sla_resolution_deadline <= warn_threshold,
            Ticket.sla_resolution_deadline > now,
            Ticket.sla_resolution_violated.is_(False),
            Ticket.sla_resolution_escalated_at.is_(None),
        )
        .all()
    )
    if not tickets:
        return
    mgr_ids = _svc_mgr_ids(db)
    for t in tickets:
        title = f"⚠️ SLA решения — 4 часа: заявка {t.number}"
        _add_notification(db, mgr_ids, title, t.id, "sla_warning_resolution")
