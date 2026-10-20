from fastapi import HTTPException


def respuesta_con_auditoria(repo, registro_id: int, mensaje: str, incluir_id: bool = False) -> dict:
    """Devuelve las marcas de tiempo generadas por la base de datos."""
    registro = repo.obtener_por_id(registro_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    respuesta = {
        "message": mensaje,
        "creado": registro["creado"],
        "actualizado": registro["actualizado"],
        "estado": registro["estado"],
    }
    if incluir_id:
        respuesta["id"] = registro_id
    return respuesta
