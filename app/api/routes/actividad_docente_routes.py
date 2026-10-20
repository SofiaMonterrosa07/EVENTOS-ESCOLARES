from fastapi import APIRouter, Depends, HTTPException

from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.security import exigir_modulo, obtener_usuario_actual
from app.models.actividad_docente import ActividadDocente
from app.repositories.actividad_docente_repository import ActividadDocenteRepository
from app.repositories.auth_repository import normalizar_nombre

router = APIRouter(prefix="/actividades-docentes", tags=["Actividad - Docente"])
repo = ActividadDocenteRepository()

ROLES_CONSULTA = ("administrador", "coordinador", "docente", "profesor", "entrenador")
ROLES_GESTION = ("administrador", "coordinador")
ROLES_DOCENTES = {"docente", "profesor", "entrenador"}


@router.get("/")
def obtener_todos(
    usuario: dict = Depends(exigir_modulo("actividades", roles_lectura=ROLES_CONSULTA)),
):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in ROLES_DOCENTES:
        return repo.obtener_por_docente(int(usuario["id"]))
    return repo.obtener_todos()


@router.get("/opciones/docentes")
def obtener_docentes_disponibles(
    usuario: dict = Depends(exigir_modulo("actividades", roles_lectura=ROLES_GESTION)),
):
    return repo.obtener_docentes_disponibles()


@router.get("/actividad/{actividad_id}")
def obtener_por_actividad(
    actividad_id: int,
    usuario: dict = Depends(exigir_modulo("actividades", roles_lectura=ROLES_GESTION)),
):
    return repo.obtener_por_actividad(actividad_id)


@router.get("/docente/{docente_id}")
def obtener_por_docente(
    docente_id: int,
    usuario: dict = Depends(exigir_modulo("actividades", roles_lectura=ROLES_CONSULTA)),
):
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in ROLES_DOCENTES and docente_id != int(usuario["id"]):
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return repo.obtener_por_docente(docente_id)


@router.get("/disponibilidad/{docente_id}")
def verificar_disponibilidad(
    docente_id: int,
    fecha: str,
    hora: str,
    usuario: dict = Depends(exigir_modulo("actividades", roles_lectura=ROLES_GESTION)),
):
    disponible = repo.verificar_disponibilidad(docente_id, fecha, hora)
    return {
        "docente_id": docente_id,
        "fecha": fecha,
        "hora": hora,
        "disponible": disponible,
        "mensaje": "Docente disponible" if disponible else "Docente ocupado a esa fecha y hora",
    }


@router.get("/{id}")
def obtener_por_id(
    id: int,
    usuario: dict = Depends(exigir_modulo("actividades", roles_lectura=ROLES_CONSULTA)),
):
    registro = repo.obtener_por_id(id)
    if not registro:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    rol = normalizar_nombre(usuario["rol_nombre"])
    if rol in ROLES_DOCENTES and int(registro["docente_id"]) != int(usuario["id"]):
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return registro


@router.post("/")
def crear_asignacion(
    data: ActividadDocente,
    usuario: dict = Depends(exigir_modulo(
        "actividades",
        modulos_escritura=("actividades",),
        roles_escritura=ROLES_GESTION,
    )),
):
    try:
        nuevo_id = repo.crear(data)
        return respuesta_con_auditoria(repo, nuevo_id, "Docente asignado a la actividad exitosamente", incluir_id=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="No fue posible asignar el docente a la actividad.") from None


@router.put("/{id}")
def actualizar_asignacion(
    id: int,
    data: ActividadDocente,
    usuario: dict = Depends(exigir_modulo(
        "actividades",
        modulos_escritura=("actividades",),
        roles_escritura=ROLES_GESTION,
    )),
):
    try:
        actualizado = repo.actualizar(id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="No fue posible actualizar la asignación del docente.") from None

    if not actualizado:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return respuesta_con_auditoria(repo, id, "Asignación actualizada exitosamente")


@router.delete("/{id}")
def eliminar_asignacion(
    id: int,
    usuario: dict = Depends(exigir_modulo(
        "actividades",
        modulos_escritura=("actividades",),
        roles_escritura=ROLES_GESTION,
    )),
):
    if repo.eliminar(id):
        return {"message": "Asignación desactivada exitosamente"}
    raise HTTPException(status_code=404, detail="Asignación no encontrada")
