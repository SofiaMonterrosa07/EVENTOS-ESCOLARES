from app.models.base import BaseRequestModel
from pydantic import Field


class NotificacionCreate(BaseRequestModel):
	usuario_id: int = Field(ge=1)
	titulo: str = Field(min_length=1, max_length=150)
	mensaje: str = Field(min_length=1, max_length=2000)
	actividad_id: int | None = Field(default=None, ge=1)
