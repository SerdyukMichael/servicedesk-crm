from datetime import datetime, timedelta

# (reaction_hours, resolution_hours) по типу договора
SLA_MATRIX: dict[str, tuple[int, int]] = {
    "full_service":      (2, 24),
    "partial":           (8, 72),
    "time_and_material": (8, 72),
    "warranty":          (8, 72),
}
SLA_DEFAULT = (8, 72)

WARN_REACTION_HOURS = 1
WARN_RESOLUTION_HOURS = 4

FINAL_STATUSES = {"completed", "closed", "cancelled"}
REACTION_DONE_STATUSES = {"in_progress", "waiting_part", "on_review", "completed", "closed", "cancelled"}


def get_sla_hours(contract_type: str | None) -> tuple[int, int]:
    return SLA_MATRIX.get(contract_type or "", SLA_DEFAULT)


def compute_sla_deadlines(
    contract_type: str | None,
    base_at: datetime,
) -> tuple[datetime, datetime]:
    rh, resh = get_sla_hours(contract_type)
    return base_at + timedelta(hours=rh), base_at + timedelta(hours=resh)
