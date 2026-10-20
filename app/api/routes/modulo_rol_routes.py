from fastapi import APIRouter, HTTPException
from app.api.routes.audit_response import respuesta_con_auditoria
from app.models.modulo_rol import ModuloRol
from app.repositories.modulo_rol_repository import ModuloRolRepository

router = APIRouter(prefix="/modulos-roles", tags=["Módulos Roles"])
repo = ModuloRolRepository()

@router.get("/")
def obtener_todos():
    return repo.obtener_todos()

@router.get("/{id}")
def obtener_por_id(id: int):
    registro = repo.obtener_por_id(id)
    if not registro:
        raise HTTPException(status_code=404, detail="Relación módulo-rol no encontrada")
    return registro

@router.post("/")
def crear_relacion(data: ModuloRol):
    nuevo_id = repo.crear(data)
    return respuesta_con_auditoria(repo, nuevo_id, "Relación módulo-rol creada exitosamente", incluir_id=True)

@router.put("/{id}")
def actualizar_relacion(id: int, data: ModuloRol):
    if repo.actualizar(id, data):
        return respuesta_con_auditoria(repo, id, "Relación módulo-rol actualizada exitosamente")
    raise HTTPException(status_code=404, detail="Relación módulo-rol no encontrada")

@router.delete("/{id}")
def eliminar_relacion(id: int):
    if repo.eliminar(id):
        return {"message": "Relación módulo-rol desactivada exitosamente"}
    raise HTTPException(status_code=404, detail="Relación módulo-rol no encontrada")