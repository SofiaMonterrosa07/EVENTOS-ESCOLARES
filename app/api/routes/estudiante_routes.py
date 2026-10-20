from fastapi import APIRouter, Depends, HTTPException
from psycopg2.errors import UniqueViolation
from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo
from app.models.estudiante import Estudiante, EstudianteAcudientesUpdate
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.estudiante_repository import EstudianteRepository
from app.repositories.usuario_repository import UsuarioRepository

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])
repo = EstudianteRepository()
usuarios_repo = UsuarioRepository()
ROLES_CONSULTA = (
    "administrador", "secretaria", "coordinador", "director", "bienestar", "orientador",
    "docente", "profesor", "entrenador", "estudiante", "acudiente", "padre o acudiente",
)
ROLES_GESTION = {"administrador", "secretaria"}
ROLES_AGREGADOS = {"bienestar", "orientador", "director"}
ROLES_DOCENTES = {"docente", "profesor", "entrenador"}
ROLES_ACUDIENTE = {"acudiente", "padre o acudiente"}

@router.get("/")
def obtener_todos(usuario: dict = Depends(exigir_modulo(
    "estudiantes", "inscripciones", "asistencia", "actividades", "autorizaciones",
    "bienestar", "analitica", "reportes", roles_lectura=ROLES_CONSULTA,
))):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in ROLES_AGREGADOS:
        return repo.obtener_resumen_bienestar()
    if rol == "coordinador":
        return repo.obtener_para_inscripciones()
    if rol in ROLES_DOCENTES:
        return repo.obtener_por_docente(int(usuario["id"]))
    if rol == "estudiante":
        return repo.obtener_por_usuario(int(usuario["id"]))
    if rol in ROLES_ACUDIENTE:
        return repo.obtener_por_acudiente(int(usuario["id"]))
    return repo.obtener_todos()


@router.get("/resumen")
def obtener_resumen(usuario: dict = Depends(exigir_modulo(
    "estudiantes", "inscripciones", "bienestar", "analitica", "reportes",
    roles_lectura=("administrador", "secretaria", "coordinador", "director", "bienestar", "orientador"),
))):
    return repo.obtener_resumen_bienestar()

@router.get("/{estudiante_id}/acudientes")
def obtener_acudientes_vinculados(
    estudiante_id: int,
    usuario: dict = Depends(exigir_modulo("estudiantes", roles_lectura=ROLES_GESTION)),
):
    return repo.obtener_acudientes_vinculados(estudiante_id)

@router.put("/{estudiante_id}/acudientes")
def actualizar_acudientes_vinculados(
    estudiante_id: int,
    datos: EstudianteAcudientesUpdate,
    usuario: dict = Depends(exigir_modulo(
        "estudiantes", modulos_escritura=("estudiantes",), roles_escritura=ROLES_GESTION
    )),
):
    try:
        total = repo.reemplazar_acudientes_vinculados(estudiante_id, datos.vinculos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"message": "Vínculos actualizados.", "cantidad": total}

@router.get("/{estudiante_id}")
def obtener_por_id(
    estudiante_id: int,
    usuario: dict = Depends(exigir_modulo(
        "estudiantes", "inscripciones", "asistencia", "actividades", "autorizaciones",
        roles_lectura=ROLES_CONSULTA,
    )),
):
    rol = normalizar_nombre(usuario["rol_nombre"])
    usuario_id = int(usuario["id"])
    if rol in ROLES_GESTION:
        estudiante = repo.obtener_por_id(estudiante_id)
    elif rol == "coordinador":
        estudiante = repo.obtener_referencia(estudiante_id)
    elif rol == "estudiante" and repo.pertenece_a_usuario(estudiante_id, usuario_id):
        estudiante = repo.obtener_referencia(estudiante_id)
    elif rol in ROLES_ACUDIENTE and repo.pertenece_a_acudiente(estudiante_id, usuario_id):
        estudiante = repo.obtener_referencia(estudiante_id)
    elif rol in ROLES_DOCENTES and repo.pertenece_a_docente(estudiante_id, usuario_id):
        estudiante = repo.obtener_referencia(estudiante_id)
    else:
        estudiante = None
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return estudiante

@router.post("/", dependencies=[Depends(exigir_modulo("estudiantes", modulos_escritura=("estudiantes",), roles_escritura=("administrador", "secretaria")))])
def crear_estudiante(estudiante: Estudiante):
    if not usuarios_repo.usuario_tiene_rol(estudiante.usuario_id, {"estudiante"}):
        raise HTTPException(status_code=400, detail="Selecciona una cuenta activa con rol de estudiante.")
    try:
        nuevo_id = repo.crear(estudiante)
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="Esta cuenta o código ya está asociado a otro estudiante.") from error
    return respuesta_con_auditoria(repo, nuevo_id, "Estudiante creado exitosamente", incluir_id=True)

@router.put("/{estudiante_id}", dependencies=[Depends(exigir_modulo("estudiantes", modulos_escritura=("estudiantes",), roles_escritura=("administrador", "secretaria")))])
def actualizar_estudiante(estudiante_id: int, estudiante: Estudiante):
    if not usuarios_repo.usuario_tiene_rol(estudiante.usuario_id, {"estudiante"}):
        raise HTTPException(status_code=400, detail="Selecciona una cuenta activa con rol de estudiante.")
    try:
        if repo.actualizar(estudiante_id, estudiante):
            return respuesta_con_auditoria(repo, estudiante_id, "Estudiante actualizado exitosamente")
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="Esta cuenta o código ya está asociado a otro estudiante.") from error
    raise HTTPException(status_code=404, detail="Estudiante no encontrado")

@router.delete("/{estudiante_id}", dependencies=[Depends(exigir_modulo("estudiantes", modulos_escritura=("estudiantes",), roles_escritura=("administrador", "secretaria")))])
def eliminar_estudiante(estudiante_id: int):
    if repo.eliminar(estudiante_id):
        return {"message": "Estudiante desactivado exitosamente"}
    raise HTTPException(status_code=404, detail="Estudiante no encontrado")
