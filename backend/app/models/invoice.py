# Re-export from canonical consolidated model
from app.models import Invoice, InvoiceItem  # noqa: F401

__all__ = ["Invoice", "InvoiceItem"]
