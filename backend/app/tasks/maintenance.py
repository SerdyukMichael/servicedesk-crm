from datetime import date, datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Equipment, MaintenanceSchedule, Notification, Ticket, User
from app.services.maintenance import calculate_next_date


@shared_task(name="app.tasks.maintenance.run_maintenance_scheduler")
def run_maintenance_scheduler():
    db: Session = SessionLocal()
    try:
        today = date.today()
        warn_date = today + timedelta(days=14)
        create_date = today + timedelta(days=7)

        schedules = (
            db.query(MaintenanceSchedule)
            .filter(MaintenanceSchedule.is_active.is_(True))
            .all()
        )

        for s in schedules:
            if s.next_date == warn_date:
                _notify_upcoming(db, s, days=14)
            elif s.next_date == create_date:
                ticket = _create_maintenance_ticket(db, s)
                if ticket:
                    s.last_ticket_id = ticket.id
                    s.next_date = calculate_next_date(s.next_date, s.frequency)
                    _notify_upcoming(db, s, days=7, created=True)

        db.commit()
    finally:
        db.close()


def _create_maintenance_ticket(db: Session, schedule: MaintenanceSchedule):
    eq = db.query(Equipment).filter(Equipment.id == schedule.equipment_id).first()
    if not eq or eq.is_deleted:
        return None

    today_str = date.today().strftime("%Y%m%d")
    count = db.query(Ticket).filter(Ticket.number.like(f"T-{today_str}-%")).count()
    number = f"T-{today_str}-{count + 1:04d}"

    FREQ_LABELS = {
        "monthly": "ежемесячное",
        "quarterly": "ежеквартальное",
        "semiannual": "полугодовое",
        "annual": "годовое",
    }
    freq_label = FREQ_LABELS.get(schedule.frequency, schedule.frequency)

    ticket = Ticket(
        number=number,
        client_id=eq.client_id,
        equipment_id=eq.id,
        created_by=schedule.created_by or 1,
        title=f"Плановое ТО ({freq_label}) — {eq.serial_number}",
        description=f"Автоматически создано по графику ТО (периодичность: {freq_label}).",
        type="maintenance",
        priority="medium",
        status="new",
    )
    db.add(ticket)
    db.flush()
    return ticket


def _notify_upcoming(db: Session, schedule: MaintenanceSchedule, days: int, created: bool = False):
    eq = db.query(Equipment).filter(Equipment.id == schedule.equipment_id).first()
    if not eq:
        return

    if created:
        title = f"📋 Создана заявка на плановое ТО: {eq.serial_number}"
    else:
        title = f"🔔 Через {days} дн. — плановое ТО: {eq.serial_number}"

    mgrs = db.query(User).filter(User.is_active.is_(True)).all()
    mgr_ids = [u.id for u in mgrs if "svc_mgr" in (u.roles or [])]

    for uid in mgr_ids:
        db.add(Notification(
            user_id=uid,
            event_type="maintenance_upcoming",
            title=title,
        ))
