from fastapi import APIRouter, Depends, HTTPException
from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo, obtener_usuario_actual
from app.models.asistencia import Asistencia
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.asistencia_repository import AsistenciaRepository

router = APIRouter(prefix="/asistencias", tags=["Asistencias"])
repo = AsistenciaRepository()
ROLES_LECTURA = ("administrador", "coordinador", "docente", "profesor", "entrenador", "estudiante", "acudiente", "padre o acudiente", "bienestar")
ROLES_CONSULTA_DETALLE = ("administrador", "coordinador", "docente", "profesor", "entrenador", "estudiante", "acudiente", "padre o acudiente")
ROLES_ANALITICA = ("administrador", "coordinador", "director", "bienestar", "orientador")


@router.get("/resumen")
def obtener_resumen(
    usuario: dict = Depends(exigir_modulo("analitica", "reportes", "bienestar", roles_lectura=ROLES_ANALITICA)),
):
    return repo.obtener_resumen()

@router.get("/", dependencies=[Depends(exigir_modulo("asistencia", "bienestar", roles_lectura=ROLES_LECTURA))])
def obtener_todos(usuario: dict = Depends(obtener_usuario_actual)):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "estudiante":
        return repo.obtener_por_usuario(int(usuario["id"]))
    if rol in {"acudiente", "padre o acudiente"}:
        return repo.obtener_por_acudiente(int(usuario["id"]))
    if rol in {"docente", "profesor", "entrenador"}:
        return repo.obtener_por_docente(int(usuario["id"]))
    if rol == "bienestar":
        return repo.obtener_resumen()
    return repo.obtener_todos()

@router.get("/{asistencia_id}", dependencies=[Depends(exigir_modulo("asistencia", roles_lectura=ROLES_CONSULTA_DETALLE))])
def obtener_por_id(asistencia_id: int, usuario: dict = Depends(obtener_usuario_actual)):
    asistencia = repo.obtener_por_id(asistencia_id)
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "estudiante" and not repo.pertenece_a_usuario(asistencia_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    if rol in {"acudiente", "padre o acudiente"} and not repo.pertenece_a_acudiente(asistencia_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    if rol in {"docente", "profesor", "entrenador"} and not repo.pertenece_a_docente(asistencia_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    return asistencia

@router.post("/", dependencies=[Depends(exigir_modulo("asistencia", modulos_escritura=("asistencia",), roles_escritura=("administrador", "coordinador", "docente", "profesor", "entrenador")))])
def crear_asistencia(asistencia: Asistencia, usuario: dict = Depends(obtener_usuario_actual)):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "coordinador" and {"nota", "retroalimentacion"} & asistencia.model_fields_set:
        raise HTTPException(status_code=403, detail="Coordinación no puede registrar notas ni retroalimentación.")
    if rol in {"docente", "profesor", "entrenador"}:
        if not asistencia.estado:
            raise HTTPException(status_code=403, detail="El personal docente no puede desactivar registros de asistencia.")
        if not repo.docente_puede_registrar(asistencia.inscripcion_id, int(usuario["id"])):
            raise HTTPException(status_code=404, detail="Inscripcion no encontrada para las actividades asignadas.")
    try:
        nuevo_id = repo.crear(asistencia)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return respuesta_con_auditoria(repo, nuevo_id, "Asistencia creada exitosamente", incluir_id=True)

@router.put("/{asistencia_id}", dependencies=[Depends(exigir_modulo("asistencia", modulos_escritura=("asistencia",), roles_escritura=("administrador", "coordinador", "docente", "profesor", "entrenador")))])
def actualizar_asistencia(asistencia_id: int, asistencia: Asistencia, usuario: dict = Depends(obtener_usuario_actual)):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "coordinador":
        if {"nota", "retroalimentacion"} & asistencia.model_fields_set:
            raise HTTPException(status_code=403, detail="Coordinacion no puede modificar notas ni retroalimentacion.")
        actual = repo.obtener_por_id(asistencia_id)
        if not actual:
            raise HTTPException(status_code=404, detail="Asistencia no encontrada")
        asistencia.nota = actual["nota"]
        asistencia.retroalimentacion = actual["retroalimentacion"]
    if rol in {"docente", "profesor", "entrenador"}:
        actual = repo.obtener_por_id(asistencia_id)
        if not actual or not repo.pertenece_a_docente(asistencia_id, int(usuario["id"])):
            raise HTTPException(status_code=404, detail="Asistencia no encontrada")
        if bool(actual["estado"]) != bool(asistencia.estado):
            raise HTTPException(status_code=403, detail="El personal docente no puede desactivar registros de asistencia.")
        if not repo.docente_puede_registrar(asistencia.inscripcion_id, int(usuario["id"])):
            raise HTTPException(status_code=404, detail="Inscripcion no encontrada para las actividades asignadas.")
    try:
        if repo.actualizar(asistencia_id, asistencia):
            return respuesta_con_auditoria(repo, asistencia_id, "Asistencia actualizada exitosamente")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=404, detail="Asistencia no encontrada")

@router.delete("/{asistencia_id}", dependencies=[Depends(exigir_modulo("asistencia", modulos_escritura=("asistencia",), roles_escritura=("administrador", "coordinador")))])
def eliminar_asistencia(asistencia_id: int, usuario: dict = Depends(obtener_usuario_actual)):
    if repo.eliminar(asistencia_id):
        return {"message": "Asistencia desactivada exitosamente"}
    raise HTTPException(status_code=404, detail="Asistencia no encontrada")
