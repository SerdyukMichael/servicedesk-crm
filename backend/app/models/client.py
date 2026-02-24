# Re-export from canonical consolidated model
from app.models import Client, Interaction  # noqa: F401

__all__ = ["Client", "Interaction"]
