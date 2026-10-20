from fastapi import APIRouter, Depends, HTTPException

from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo, obtener_usuario_actual
from app.models.autorizacion import Autorizacion, AutorizacionConsentimiento
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.autorizacion_repository import AutorizacionRepository


router = APIRouter(prefix="/autorizaciones", tags=["Autorizaciones"])
repo = AutorizacionRepository()
MODULOS_LECTURA = ("autorizaciones",)
ROLES_GESTION = ("administrador", "coordinador")
ROLES_ACUDIENTE = {"acudiente", "padre o acudiente"}
ROLES_LECTURA = ("administrador", "coordinador", "acudiente", "padre o acudiente", "estudiante")
ROLES_ANALITICA = ("administrador", "coordinador", "director")


@router.get("/resumen")
def obtener_resumen(
    usuario: dict = Depends(exigir_modulo("analitica", "reportes", roles_lectura=ROLES_ANALITICA)),
):
    return repo.obtener_resumen()


@router.get("/")
def obtener_todos(usuario: dict = Depends(exigir_modulo(*MODULOS_LECTURA, roles_lectura=ROLES_LECTURA))):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in ROLES_ACUDIENTE:
        return repo.obtener_por_acudiente(int(usuario["id"]))
    if rol == "estudiante":
        return repo.obtener_por_estudiante(int(usuario["id"]))
    return repo.obtener_todos()


@router.get("/{autorizacion_id}")
def obtener_por_id(
    autorizacion_id: int,
    usuario: dict = Depends(exigir_modulo(*MODULOS_LECTURA, roles_lectura=ROLES_LECTURA)),
):
    autorizacion = repo.obtener_por_id(autorizacion_id)
    if not autorizacion:
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in ROLES_ACUDIENTE and not repo.pertenece_a_acudiente(autorizacion_id, int(usuario["id"])):
        raise HTTPException(status_code=404, detail="Autorización no encontrada")
    if rol == "estudiante":
        autorizacion_propia = repo.obtener_por_id_para_estudiante(autorizacion_id, int(usuario["id"]))
        if not autorizacion_propia:
            raise HTTPException(status_code=404, detail="Autorización no encontrada")
        return autorizacion_propia
    return autorizacion


@router.patch("/{autorizacion_id}/consentimiento")
def responder_autorizacion(
    autorizacion_id: int,
    respuesta: AutorizacionConsentimiento,
    usuario: dict = Depends(exigir_modulo("autorizaciones")),
):
    if normalizar_nombre(usuario["rol_nombre"]) not in ROLES_ACUDIENTE:
        raise HTTPException(status_code=403, detail="Esta acción está reservada al acudiente asociado.")
    if repo.actualizar_respuesta_acudiente(autorizacion_id, int(usuario["id"]), respuesta.estado):
        return {"message": "Respuesta de autorización guardada"}
    raise HTTPException(status_code=404, detail="Autorización no encontrada")


@router.post("/")
def crear_autorizacion(
    autorizacion: Autorizacion,
    usuario: dict = Depends(exigir_modulo("autorizaciones", modulos_escritura=("autorizaciones",), roles_escritura=ROLES_GESTION)),
):
    nuevo_id = repo.crear(autorizacion)
    return respuesta_con_auditoria(repo, nuevo_id, "Autorización creada exitosamente", incluir_id=True)


@router.put("/{autorizacion_id}")
def actualizar_autorizacion(
    autorizacion_id: int,
    autorizacion: Autorizacion,
    usuario: dict = Depends(exigir_modulo("autorizaciones", modulos_escritura=("autorizaciones",), roles_escritura=ROLES_GESTION)),
):
    if repo.actualizar(autorizacion_id, autorizacion):
        return respuesta_con_auditoria(repo, autorizacion_id, "Autorización actualizada exitosamente")
    raise HTTPException(status_code=404, detail="Autorización no encontrada")


@router.delete("/{autorizacion_id}")
def eliminar_autorizacion(
    autorizacion_id: int,
    usuario: dict = Depends(exigir_modulo("autorizaciones", modulos_escritura=("autorizaciones",), roles_escritura=ROLES_GESTION)),
):
    raise HTTPException(
        status_code=405,
        detail="Las autorizaciones conservan su historial; registra una nueva respuesta o corrige el estado autorizado.",
    )
