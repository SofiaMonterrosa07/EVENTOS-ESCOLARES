from fastapi import APIRouter, Depends, HTTPException
from psycopg2.errors import UniqueViolation
from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo
from app.models.acudiente import Acudiente, AcudienteVinculosUpdate
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.acudiente_repository import AcudienteRepository
from app.repositories.usuario_repository import UsuarioRepository

router = APIRouter(prefix="/acudientes", tags=["Acudientes"])
repo = AcudienteRepository()
usuarios_repo = UsuarioRepository()
ROLES_GESTION = ("administrador", "secretaria")

@router.get("/")
def obtener_todos(usuario: dict = Depends(exigir_modulo(
    "acudientes", "autorizaciones",
    roles_lectura=("administrador", "secretaria", "coordinador", "acudiente", "padre o acudiente"),
))):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol == "coordinador":
        return repo.obtener_para_autorizacion()
    if rol in {"acudiente", "padre o acudiente"}:
        registro = repo.obtener_por_usuario(int(usuario["id"]))
        return [registro] if registro else []
    return repo.obtener_todos()


@router.get("/resumen")
def obtener_resumen(usuario: dict = Depends(exigir_modulo(
    "acudientes", roles_lectura=("administrador", "secretaria"),
))):
    return repo.obtener_resumen()


@router.get("/{acudiente_id}/estudiantes")
def obtener_estudiantes_vinculados(
    acudiente_id: int,
    usuario: dict = Depends(exigir_modulo("acudientes", roles_lectura=ROLES_GESTION)),
):
    return repo.obtener_estudiantes_vinculados(acudiente_id)


@router.put("/{acudiente_id}/estudiantes")
def actualizar_estudiantes_vinculados(
    acudiente_id: int,
    datos: AcudienteVinculosUpdate,
    usuario: dict = Depends(exigir_modulo(
        "acudientes", modulos_escritura=("acudientes",), roles_escritura=ROLES_GESTION
    )),
):
    try:
        total = repo.reemplazar_estudiantes_vinculados(acudiente_id, datos.vinculos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"message": "Vínculos actualizados.", "cantidad": total}

@router.get("/{acudiente_id}")
def obtener_por_id(
    acudiente_id: int,
    usuario: dict = Depends(exigir_modulo(
        "acudientes", "autorizaciones",
        roles_lectura=("administrador", "secretaria", "coordinador", "acudiente", "padre o acudiente"),
    )),
):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in {"administrador", "secretaria"}:
        acudiente = repo.obtener_por_id(acudiente_id)
    elif rol == "coordinador":
        acudiente = repo.obtener_referencia(acudiente_id)
    elif rol in {"acudiente", "padre o acudiente"} and repo.pertenece_a_usuario(acudiente_id, int(usuario["id"])):
        acudiente = repo.obtener_por_usuario(int(usuario["id"]))
    else:
        acudiente = None
    if not acudiente:
        raise HTTPException(status_code=404, detail="Acudiente no encontrado")
    return acudiente

@router.post("/")
def crear_acudiente(acudiente: Acudiente, usuario: dict = Depends(exigir_modulo("acudientes", modulos_escritura=("acudientes",), roles_escritura=("administrador", "secretaria")))):
    if not usuarios_repo.usuario_tiene_rol(acudiente.usuario_id, {"acudiente", "padre o acudiente"}):
        raise HTTPException(status_code=400, detail="Selecciona una cuenta activa con rol de acudiente.")
    try:
        nuevo_id = repo.crear(acudiente)
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="Esta cuenta o documento ya está asociado a otro acudiente.") from error
    return respuesta_con_auditoria(repo, nuevo_id, "Acudiente creado exitosamente", incluir_id=True)

@router.put("/{acudiente_id}")
def actualizar_acudiente(acudiente_id: int, acudiente: Acudiente, usuario: dict = Depends(exigir_modulo("acudientes", modulos_escritura=("acudientes",), roles_escritura=("administrador", "secretaria")))):
    if not usuarios_repo.usuario_tiene_rol(acudiente.usuario_id, {"acudiente", "padre o acudiente"}):
        raise HTTPException(status_code=400, detail="Selecciona una cuenta activa con rol de acudiente.")
    try:
        if repo.actualizar(acudiente_id, acudiente):
            return respuesta_con_auditoria(repo, acudiente_id, "Acudiente actualizado exitosamente")
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="Esta cuenta o documento ya está asociado a otro acudiente.") from error
    raise HTTPException(status_code=404, detail="Acudiente no encontrado")

@router.delete("/{acudiente_id}")
def eliminar_acudiente(acudiente_id: int, usuario: dict = Depends(exigir_modulo("acudientes", modulos_escritura=("acudientes",), roles_escritura=("administrador", "secretaria")))):
    if repo.eliminar(acudiente_id):
        return {"message": "Acudiente desactivado exitosamente"}
    raise HTTPException(status_code=404, detail="Acudiente no encontrado")
