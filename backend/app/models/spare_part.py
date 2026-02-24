# Re-export from canonical consolidated model
from app.models import SparePart, PartsUsage  # noqa: F401

__all__ = ["SparePart", "PartsUsage"]
