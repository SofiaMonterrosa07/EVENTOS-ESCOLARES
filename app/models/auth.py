from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    correo: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    rol_id: int = Field(ge=1)

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, value: str) -> str:
        return value.strip().lower()
