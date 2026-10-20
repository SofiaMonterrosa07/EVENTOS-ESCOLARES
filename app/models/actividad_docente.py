from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import datetime
from typing import Optional

class ActividadDocente(BaseRequestModel):
    id: Optional[int] = None
    actividad_id: int
    docente_id: int
    rol_en_actividad: Optional[str] = "Acompañante"
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool
