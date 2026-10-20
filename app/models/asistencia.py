from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import datetime
from decimal import Decimal
from typing import Optional

class Asistencia(BaseRequestModel):
    id: Optional[int] = None
    inscripcion_id: int
    asistio: Optional[StrictBool] = None
    observacion: Optional[str] = None
    nota: Optional[Decimal] = Field(default=None, ge=0, le=5, max_digits=3, decimal_places=2)
    retroalimentacion: Optional[str] = Field(default=None, max_length=1000)
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool
