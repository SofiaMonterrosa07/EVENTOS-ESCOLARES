from pydantic import BaseModel, ConfigDict, model_validator


class BaseRequestModel(BaseModel):
    # Request bodies may contain timestamps returned by GET, but those values
    # are ignored and never reach INSERT/UPDATE statements.
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def ignorar_fechas_de_auditoria_recibidas(cls, valores):
        """Las fechas son generadas por PostgreSQL, nunca por el cliente."""
        if isinstance(valores, dict):
            valores = valores.copy()
            valores.pop("creado", None)
            valores.pop("actualizado", None)
        return valores
