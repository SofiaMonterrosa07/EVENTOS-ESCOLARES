from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import datetime
from typing import Optional

class Autorizacion(BaseRequestModel):
    id: Optional[int] = None
    inscripcion_id: int
    acudiente_id: int
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool
    fecha_autorizacion: Optional[str] = None  # Formato: "YYYY-MM-DD"


class AutorizacionConsentimiento(BaseRequestModel):
    """El acudiente únicamente puede cambiar su respuesta de autorización."""
    estado: StrictBool
