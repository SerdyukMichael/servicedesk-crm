# Re-export from canonical consolidated model
from app.models import EquipmentCatalog, ClientEquipment  # noqa: F401

__all__ = ["EquipmentCatalog", "ClientEquipment"]
