from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import datetime
from typing import Optional

class Acudiente(BaseRequestModel):
    id: Optional[int] = None
    usuario_id: int
    documento: str
    telefono: str
    parentesco: Optional[str] = None
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool


class AcudienteVinculo(BaseRequestModel):
    estudiante_id: int = Field(ge=1)
    parentesco: Optional[str] = Field(default=None, max_length=50)


class AcudienteVinculosUpdate(BaseRequestModel):
    vinculos: list[AcudienteVinculo] = Field(default_factory=list)
