from datetime import date

from dateutil.relativedelta import relativedelta

FREQ_MONTHS = {
    "monthly":    1,
    "quarterly":  3,
    "semiannual": 6,
    "annual":     12,
}


def calculate_next_date(current: date, frequency: str) -> date:
    months = FREQ_MONTHS[frequency]
    return current + relativedelta(months=months)
