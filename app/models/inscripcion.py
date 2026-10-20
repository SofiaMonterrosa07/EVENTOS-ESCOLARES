from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import date, datetime
from typing import Optional

class Inscripcion(BaseRequestModel):
    id: Optional[int] = None
    estudiante_id: int
    actividad_id: int
    fecha_inscripcion: Optional[date] = None
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool


class InscripcionPropiaCreate(BaseRequestModel):
    """Solicitud de inscripción; el estudiante se deriva de la sesión."""
    actividad_id: int = Field(ge=1)


class InscripcionAcudidoCreate(BaseRequestModel):
    """El estudiante solicitado se valida contra el vínculo del acudiente."""
    estudiante_id: int = Field(ge=1)
    actividad_id: int = Field(ge=1)
