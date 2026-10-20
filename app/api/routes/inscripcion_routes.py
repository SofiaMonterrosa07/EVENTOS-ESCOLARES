from fastapi import APIRouter, Depends, HTTPException
from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo, obtener_usuario_actual
from app.models.inscripcion import Inscripcion, InscripcionAcudidoCreate, InscripcionPropiaCreate
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.inscripcion_repository import InscripcionRepository

router = APIRouter(prefix="/inscripciones", tags=["Inscripciones"])
repo = InscripcionRepository()
ROLES_LECTURA = ("administrador", "coordinador", "docente", "profesor", "estudiante", "acudiente", "padre o acudiente", "entrenador")

@router.get("/resumen", dependencies=[Depends(exigir_modulo("inscripciones", "actividades", "calendario", "eventos", "cupos", "autorizaciones", "asistencia", "bienestar", "reportes", "analitica", "auditoria"))])
def resumen_actividades():
    return repo.resumen_actividades()

@router.get("/resumen-institucional", dependencies=[Depends(exigir_modulo("reportes", "analitica", roles_lectura=("administrador", "coordinador", "director")))])
def resumen_institucional_actividades():
    return repo.resumen_institucional_actividades()

@router.get("/", dependencies=[Depends(exigir_modulo("inscripciones", roles_lectura=ROLES_LECTURA))])
def obtener_todos(usuario: dict = Depends(obtener_usuario_actual)):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "estudiante":
        return repo.obtener_por_usuario(int(usuario["id"]))
    if rol in {"acudiente", "padre o acudiente"}:
        return repo.obtener_por_acudiente(int(usuario["id"]))
    if rol in {"docente", "profesor", "entrenador"}:
        return repo.obtener_por_docente(int(usuario["id"]))
    return repo.obtener_todos()


@router.post("/propias")
def crear_inscripcion_propia(
    datos: InscripcionPropiaCreate,
    usuario: dict = Depends(exigir_modulo(
        "inscripciones", modulos_escritura=("inscripciones",), roles_escritura=("estudiante",)
    )),
):
    try:
        nuevo_id = repo.crear_para_usuario(int(usuario["id"]), datos.actividad_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"message": "Inscripción creada exitosamente", "id": nuevo_id}


@router.post("/acudidos")
def crear_inscripcion_acudido(
    datos: InscripcionAcudidoCreate,
    usuario: dict = Depends(exigir_modulo(
        "inscripciones", modulos_escritura=("inscripciones",),
        roles_escritura=("acudiente", "padre o acudiente"),
    )),
):
    try:
        nuevo_id = repo.crear_para_acudido(int(usuario["id"]), datos.estudiante_id, datos.actividad_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"message": "Inscripción y autorización pendiente creadas", "id": nuevo_id}


@router.delete("/propias/{inscripcion_id}")
def cancelar_inscripcion_propia(
    inscripcion_id: int,
    usuario: dict = Depends(exigir_modulo(
        "inscripciones", modulos_escritura=("inscripciones",), roles_escritura=("estudiante",)
    )),
):
    if repo.cancelar_para_usuario(inscripcion_id, int(usuario["id"])):
        return {"message": "Inscripción cancelada"}
    raise HTTPException(status_code=404, detail="No hay una inscripción activa cancelable para este perfil.")


@router.delete("/acudidos/{inscripcion_id}")
def cancelar_inscripcion_acudido(
    inscripcion_id: int,
    usuario: dict = Depends(exigir_modulo(
        "inscripciones", modulos_escritura=("inscripciones",),
        roles_escritura=("acudiente", "padre o acudiente"),
    )),
):
    if repo.cancelar_para_acudiente(inscripcion_id, int(usuario["id"])):
        return {"message": "Inscripción cancelada"}
    raise HTTPException(status_code=404, detail="No hay una inscripción activa cancelable para este perfil.")

@router.get("/{inscripcion_id}", dependencies=[Depends(exigir_modulo("inscripciones", roles_lectura=ROLES_LECTURA))])
def obtener_por_id(inscripcion_id: int, usuario: dict = Depends(obtener_usuario_actual)):
    inscripcion = repo.obtener_por_id(inscripcion_id)
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "estudiante" and not repo.pertenece_a_usuario(inscripcion_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    if rol in {"acudiente", "padre o acudiente"} and not repo.pertenece_a_acudiente(inscripcion_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    if rol in {"docente", "profesor", "entrenador"} and not repo.pertenece_a_docente(inscripcion_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return inscripcion

@router.post("/", dependencies=[Depends(exigir_modulo("inscripciones", modulos_escritura=("inscripciones",), roles_escritura=("administrador", "coordinador")))])
def crear_inscripcion(inscripcion: Inscripcion):
    try:
        nuevo_id = repo.crear(inscripcion)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return respuesta_con_auditoria(repo, nuevo_id, "Inscripción creada exitosamente", incluir_id=True)

@router.put("/{inscripcion_id}", dependencies=[Depends(exigir_modulo("inscripciones", modulos_escritura=("inscripciones",), roles_escritura=("administrador", "coordinador")))])
def actualizar_inscripcion(inscripcion_id: int, inscripcion: Inscripcion):
    try:
        if repo.actualizar(inscripcion_id, inscripcion):
            return respuesta_con_auditoria(repo, inscripcion_id, "Inscripción actualizada exitosamente")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=404, detail="Inscripción no encontrada")

@router.delete("/{inscripcion_id}", dependencies=[Depends(exigir_modulo("inscripciones", modulos_escritura=("inscripciones",), roles_escritura=("administrador", "coordinador")))])
def eliminar_inscripcion(inscripcion_id: int):
    if repo.eliminar(inscripcion_id):
        return {"message": "Inscripción desactivada exitosamente"}
    raise HTTPException(status_code=404, detail="Inscripción no encontrada")
