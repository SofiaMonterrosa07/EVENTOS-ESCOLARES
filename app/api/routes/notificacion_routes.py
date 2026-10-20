from fastapi import APIRouter, Depends, HTTPException

from app.core.security import exigir_modulo
from app.models.notificacion import NotificacionCreate
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.notificacion_repository import NotificacionRepository


router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])
repo = NotificacionRepository()
ROLES_LECTURA = (
	"administrador", "coordinador", "docente", "profesor", "entrenador", "estudiante",
	"acudiente", "padre o acudiente", "director", "bienestar", "orientador", "secretaria",
)


@router.get("/")
def obtener_todas(
	usuario: dict = Depends(exigir_modulo("notificaciones", roles_lectura=ROLES_LECTURA)),
):
	return repo.obtener_por_usuario(int(usuario["id"]))


@router.get("/{notificacion_id}")
def obtener_por_id(
	notificacion_id: int,
	usuario: dict = Depends(exigir_modulo("notificaciones", roles_lectura=ROLES_LECTURA)),
):
	registro = repo.obtener_por_id(notificacion_id, int(usuario["id"]))
	if not registro:
		raise HTTPException(status_code=404, detail="Notificación no encontrada")
	return registro


@router.patch("/{notificacion_id}/leida")
def marcar_leida(
	notificacion_id: int,
	usuario: dict = Depends(exigir_modulo("notificaciones", modulos_escritura=("notificaciones",), roles_escritura=ROLES_LECTURA)),
):
	if repo.marcar_leida(notificacion_id, int(usuario["id"])):
		return {"message": "Notificación marcada como leída"}
	raise HTTPException(status_code=404, detail="Notificación no encontrada")


@router.post("/")
def crear_notificacion(
	notificacion: NotificacionCreate,
	usuario: dict = Depends(exigir_modulo(
		"notificaciones", modulos_escritura=("notificaciones",), roles_escritura=("administrador",)
	)),
):
	if normalizar_nombre(usuario["rol_nombre"]) != "administrador":
		raise HTTPException(status_code=403, detail="Solo administración puede enviar notificaciones.")
	try:
		identificador = repo.crear(notificacion, int(usuario["id"]))
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error
	return {"message": "Notificación enviada", "id": identificador}
