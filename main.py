import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

load_dotenv()

from app.api.routes import (
    rol_routes, usuario_routes, modulo_routes, modulo_rol_routes,
    estudiante_routes, acudiente_routes, categoria_actividad_routes,
    actividad_routes, inscripcion_routes, autorizacion_routes,
    asistencia_routes, actividad_docente_routes,
    auth_routes, notificacion_routes
)
from app.core.security import exigir_modulo

ORIGENES_CORS_POR_DEFECTO = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
ORIGENES_CORS_CONFIGURADOS = [
    origen.strip().rstrip("/")
    for origen in os.getenv("CORS_ORIGINS", "").split(",")
    if origen.strip()
]

app = FastAPI(
    title="Colegio san Miguel: Area de gestoria para Eventos y Actividades extracurriculares",
    description="API para gestión de actividades extracurriculares con autorización digital - Colegio san Miguel",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = BASE_DIR / "app" / "static" / "favicon.ico"
    return FileResponse(icon_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_CORS_CONFIGURADOS or ORIGENES_CORS_POR_DEFECTO,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(rol_routes.router, dependencies=[Depends(exigir_modulo("roles", modulos_escritura=("roles",), roles_escritura=("administrador",)))])
app.include_router(usuario_routes.router, dependencies=[Depends(exigir_modulo("usuarios", modulos_escritura=("usuarios",), roles_lectura=("administrador", "secretaria"), roles_escritura=("administrador", "secretaria")))])
app.include_router(modulo_routes.router, dependencies=[Depends(exigir_modulo("roles", modulos_escritura=("roles",), roles_lectura=("administrador",), roles_escritura=("administrador",)))])
app.include_router(modulo_rol_routes.router, dependencies=[Depends(exigir_modulo("roles", "seguridad", modulos_escritura=("roles", "seguridad"), roles_escritura=("administrador",)))])
app.include_router(estudiante_routes.router)
app.include_router(acudiente_routes.router)
app.include_router(categoria_actividad_routes.router, dependencies=[Depends(exigir_modulo("categorias", "actividades", modulos_escritura=("categorias",), roles_escritura=("administrador", "coordinador")))])
app.include_router(actividad_routes.router, dependencies=[Depends(exigir_modulo("actividades", modulos_escritura=("actividades",), roles_escritura=("administrador", "coordinador")))])
app.include_router(inscripcion_routes.router)
app.include_router(autorizacion_routes.router)
app.include_router(asistencia_routes.router)
app.include_router(actividad_docente_routes.router, dependencies=[Depends(exigir_modulo("actividades", modulos_escritura=("actividades",), roles_escritura=("administrador", "coordinador")))])
app.include_router(notificacion_routes.router)

@app.get("/")
def root():
    return {
        "Colegio": "Colegio san Miguel",
        "message": "API Gestión de Eventos y Actividades Extracurriculares",
        "docs": "/docs",
        "status": "Funcionando correctamente"
    }
