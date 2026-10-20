from app.models.base import BaseRequestModel
from pydantic import Field, StrictBool
from datetime import datetime
from typing import Optional


class UsuarioCreate(BaseRequestModel):
    nombre: str = Field(min_length=1, max_length=150)
    correo: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    rol_id: int = Field(ge=1)
    estado: StrictBool
    grado: Optional[str] = Field(default=None, max_length=30)
    documento: Optional[str] = Field(default=None, max_length=30)
    telefono: Optional[str] = Field(default=None, max_length=30)
    parentesco: Optional[str] = Field(default=None, max_length=50)


class UsuarioUpdate(BaseRequestModel):
    nombre: str = Field(min_length=1, max_length=150)
    correo: str = Field(min_length=3, max_length=254)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    rol_id: int = Field(ge=1)
    estado: StrictBool


class UsuarioPublic(BaseRequestModel):
    id: int
    nombre: str
    correo: str
    rol_id: int
    rol_nombre: str
    creado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    actualizado: Optional[datetime] = Field(default=None, json_schema_extra={"readOnly": True})
    estado: StrictBool
