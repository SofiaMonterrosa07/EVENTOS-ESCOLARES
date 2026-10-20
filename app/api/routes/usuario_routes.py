from fastapi import APIRouter, Depends, HTTPException
from psycopg2.errors import UniqueViolation
from app.api.routes.audit_response import respuesta_con_auditoria
from app.core.passwords import hash_password
from app.core.security import exigir_modulo
from app.models.usuario import UsuarioCreate, UsuarioPublic, UsuarioUpdate
from app.repositories.auth_repository import normalizar_nombre
from app.repositories.usuario_repository import UsuarioRepository

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
repo = UsuarioRepository()
ROLES_SECRETARIA = {"estudiante", "acudiente", "padre o acudiente"}


def es_secretaria(usuario: dict) -> bool:
    return normalizar_nombre(usuario["rol_nombre"]) == "secretaria"


def es_rol_de_estudiante_o_acudiente(nombre: str | None) -> bool:
    return normalizar_nombre(nombre or "") in ROLES_SECRETARIA

@router.get("/", response_model=list[UsuarioPublic])
def obtener_todos(
    rol: str | None = None,
    usuario: dict = Depends(exigir_modulo("usuarios", roles_lectura=("administrador", "secretaria"))),
):
    usuarios = repo.obtener_todos()
    if es_secretaria(usuario):
        usuarios = [item for item in usuarios if es_rol_de_estudiante_o_acudiente(item["rol_nombre"])]
    if rol:
        rol_solicitado = normalizar_nombre(rol)
        if rol_solicitado == "acudiente":
            usuarios = [item for item in usuarios if normalizar_nombre(item["rol_nombre"]) in {"acudiente", "padre o acudiente"}]
        elif rol_solicitado == "estudiante":
            usuarios = [item for item in usuarios if normalizar_nombre(item["rol_nombre"]) == "estudiante"]
        else:
            raise HTTPException(status_code=400, detail="El filtro de rol no es válido.")
        usuarios = [item for item in usuarios if item["estado"]]
    return usuarios


@router.get("/resumen")
def obtener_resumen(
    usuario: dict = Depends(exigir_modulo("usuarios", roles_lectura=("administrador", "secretaria"))),
):
    conteos = repo.obtener_resumen()
    if es_secretaria(usuario):
        return [
            fila for fila in conteos
            if es_rol_de_estudiante_o_acudiente(fila["rol"])
        ]
    return conteos

@router.get("/{usuario_id}", response_model=UsuarioPublic)
def obtener_por_id(
    usuario_id: int,
    usuario_actual: dict = Depends(exigir_modulo("usuarios", roles_lectura=("administrador", "secretaria"))),
):
    usuario = repo.obtener_por_id(usuario_id)
    if not usuario or (es_secretaria(usuario_actual) and not es_rol_de_estudiante_o_acudiente(usuario["rol_nombre"])):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/")
def crear_usuario(
    usuario: UsuarioCreate,
    usuario_actual: dict = Depends(exigir_modulo(
        "usuarios", modulos_escritura=("usuarios",), roles_escritura=("administrador", "secretaria")
    )),
):
    rol_destino = repo.obtener_nombre_rol(usuario.rol_id)
    if not rol_destino:
        raise HTTPException(status_code=400, detail="Selecciona un rol activo.")
    if es_secretaria(usuario_actual) and not es_rol_de_estudiante_o_acudiente(rol_destino):
        raise HTTPException(status_code=403, detail="Secretaría solo puede crear cuentas de estudiantes y acudientes.")
    datos_estudiante = None
    datos_acudiente = None
    rol_normalizado = normalizar_nombre(rol_destino)
    if rol_normalizado == "estudiante":
        grado = (usuario.grado or "").strip()
        if not grado:
            raise HTTPException(
                status_code=400,
                detail="Para crear una cuenta de estudiante, indica el grado.",
            )
        datos_estudiante = {"grado": grado}
    elif rol_normalizado in {"acudiente", "padre o acudiente"}:
        documento = (usuario.documento or "").strip()
        telefono = (usuario.telefono or "").strip()
        if not documento or not telefono:
            raise HTTPException(
                status_code=400,
                detail="Para crear una cuenta de acudiente, indica el documento y el teléfono.",
            )
        datos_acudiente = {
            "documento": documento,
            "telefono": telefono,
            "parentesco": (usuario.parentesco or "").strip() or None,
        }

    datos = usuario.model_copy(update={"password": hash_password(usuario.password)})
    try:
        nuevo_id = repo.crear(
            datos,
            datos_estudiante=datos_estudiante,
            datos_acudiente=datos_acudiente,
        )
    except UniqueViolation as error:
        restriccion = getattr(getattr(error, "diag", None), "constraint_name", "")
        if restriccion == "acudiente_documento_key":
            raise HTTPException(status_code=409, detail="Ese documento ya está registrado para otro acudiente.") from error
        if restriccion == "acudiente_usuario_id_key":
            raise HTTPException(status_code=409, detail="Esta cuenta ya tiene una ficha en el módulo de acudientes.") from error
        if restriccion == "usuario_correo_key":
            raise HTTPException(status_code=409, detail="Ese correo ya está registrado.") from error
        raise HTTPException(status_code=409, detail="Ya existe un registro con uno de los datos ingresados.") from error
    return respuesta_con_auditoria(repo, nuevo_id, "Usuario creado exitosamente", incluir_id=True)

@router.put("/{usuario_id}")
def actualizar_usuario(
    usuario_id: int,
    usuario: UsuarioUpdate,
    usuario_actual: dict = Depends(exigir_modulo(
        "usuarios", modulos_escritura=("usuarios",), roles_escritura=("administrador", "secretaria")
    )),
):
    existente = repo.obtener_por_id(usuario_id)
    if not existente:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not repo.obtener_nombre_rol(usuario.rol_id):
        raise HTTPException(status_code=400, detail="Selecciona un rol activo.")
    if es_secretaria(usuario_actual):
        if not es_rol_de_estudiante_o_acudiente(existente["rol_nombre"]):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if int(usuario.rol_id) != int(existente["rol_id"]):
            raise HTTPException(status_code=403, detail="Secretaría no puede cambiar el rol de una cuenta.")
    password_hash = hash_password(usuario.password) if usuario.password else None
    datos = usuario.model_copy(update={"password": password_hash})
    if repo.actualizar(usuario_id, datos):
        return respuesta_con_auditoria(repo, usuario_id, "Usuario actualizado exitosamente")
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: int,
    usuario_actual: dict = Depends(exigir_modulo(
        "usuarios", modulos_escritura=("usuarios",), roles_escritura=("administrador", "secretaria")
    )),
):
    existente = repo.obtener_por_id(usuario_id)
    if not existente or (es_secretaria(usuario_actual) and not es_rol_de_estudiante_o_acudiente(existente["rol_nombre"])):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if repo.eliminar(usuario_id):
        return {"message": "Usuario desactivado exitosamente"}
    raise HTTPException(status_code=404, detail="Usuario no encontrado")
