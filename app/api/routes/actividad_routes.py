from fastapi import APIRouter, Depends, HTTPException
from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo, obtener_usuario_actual
from app.models.actividad import Actividad, ActividadAsociacionesUpdate
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.actividad_repository import ActividadRepository

router = APIRouter(prefix="/actividades", tags=["Actividades"])
repo = ActividadRepository()
modulos_lectura = ("actividades",)
modulos_escritura = ("actividades",)

@router.get("/", dependencies=[Depends(exigir_modulo(*modulos_lectura))])
def obtener_todos(usuario: dict = Depends(obtener_usuario_actual)):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "estudiante":
        return repo.obtener_publicas()
    if rol in {"acudiente", "padre o acudiente"}:
        return repo.obtener_por_acudiente(int(usuario["id"]))
    if rol in {"docente", "profesor", "entrenador"}:
        return repo.obtener_por_docente(int(usuario["id"]))
    return repo.obtener_todos()

@router.get("/{actividad_id}", dependencies=[Depends(exigir_modulo(*modulos_lectura))])
def obtener_por_id(actividad_id: int, usuario: dict = Depends(obtener_usuario_actual)):
    actividad = repo.obtener_por_id(actividad_id)
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "estudiante" and not repo.es_publica(actividad_id):
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if rol in {"acudiente", "padre o acudiente"} and not repo.pertenece_a_acudido(actividad_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if rol in {"docente", "profesor", "entrenador"} and not repo.pertenece_a_docente(actividad_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    return actividad

@router.get("/{actividad_id}/asociaciones")
def obtener_asociaciones(actividad_id: int, usuario: dict = Depends(exigir_modulo(
    "actividades", roles_lectura=("administrador", "coordinador"),
))):
    asociaciones = repo.obtener_asociaciones(actividad_id)
    if asociaciones is None:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    return asociaciones

@router.put("/{actividad_id}/asociaciones")
def actualizar_asociaciones(
    actividad_id: int,
    datos: ActividadAsociacionesUpdate,
    usuario: dict = Depends(exigir_modulo(
        "actividades", modulos_escritura=modulos_escritura, roles_escritura=("administrador", "coordinador"),
    )),
):
    try:
        cantidad = repo.reemplazar_asociaciones(actividad_id, datos.docente_ids, datos.estudiante_ids)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"message": "Asociaciones actualizadas.", **cantidad}

@router.post("/", dependencies=[Depends(exigir_modulo(*modulos_lectura, modulos_escritura=modulos_escritura))])
def crear_actividad(actividad: Actividad):
    try:
        nuevo_id = repo.crear(actividad)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return respuesta_con_auditoria(repo, nuevo_id, "Actividad creada exitosamente", incluir_id=True)

@router.put("/{actividad_id}", dependencies=[Depends(exigir_modulo(*modulos_lectura, modulos_escritura=modulos_escritura))])
def actualizar_actividad(actividad_id: int, actividad: Actividad):
    try:
        if repo.actualizar(actividad_id, actividad):
            return respuesta_con_auditoria(repo, actividad_id, "Actividad actualizada exitosamente")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=404, detail="Actividad no encontrada")

@router.delete("/{actividad_id}", dependencies=[Depends(exigir_modulo(*modulos_lectura, modulos_escritura=modulos_escritura))])
def eliminar_actividad(actividad_id: int):
    if repo.eliminar(actividad_id):
        return {"message": "Actividad desactivada exitosamente"}
    raise HTTPException(status_code=404, detail="Actividad no encontrada")
