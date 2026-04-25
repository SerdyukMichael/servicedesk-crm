from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "servicedesk",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.sla",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.timezone = "Europe/Moscow"
celery_app.conf.enable_utc = True

celery_app.conf.beat_schedule = {
    "sla-check-every-minute": {
        "task": "app.tasks.sla.check_sla_deadlines",
        "schedule": crontab(minute="*"),
    },
    "maintenance-daily-0800": {
        "task": "app.tasks.maintenance.run_maintenance_scheduler",
        "schedule": crontab(hour=8, minute=0),
    },
}
