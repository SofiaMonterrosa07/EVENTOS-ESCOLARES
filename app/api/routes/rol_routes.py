from fastapi import APIRouter, HTTPException
from app.api.routes.audit_response import respuesta_con_auditoria
from app.models.rol import Rol
from app.repositories.rol_repository import RolRepository

router = APIRouter(prefix="/roles", tags=["Roles"])
repo = RolRepository()

@router.get("/")
def obtener_todos():
    return repo.obtener_todos()

@router.get("/{rol_id}")
def obtener_por_id(rol_id: int):
    rol = repo.obtener_por_id(rol_id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol

@router.post("/")
def crear_rol(rol: Rol):
    nuevo_id = repo.crear(rol)
    return respuesta_con_auditoria(repo, nuevo_id, "Rol creado exitosamente-Colegio san Miguel", incluir_id=True)

@router.put("/{rol_id}")
def actualizar_rol(rol_id: int, rol: Rol):
    if repo.actualizar(rol_id, rol):
        return respuesta_con_auditoria(repo, rol_id, "Rol actualizado exitosamente-Colegio san Miguel")
    raise HTTPException(status_code=404, detail="Rol no encontrado")

@router.delete("/{rol_id}")
def eliminar_rol(rol_id: int):
    if repo.eliminar(rol_id):
        return {"message": "Rol desactivado exitosamente-Colegio san Miguel"}
    raise HTTPException(status_code=404, detail="Rol no encontrado")