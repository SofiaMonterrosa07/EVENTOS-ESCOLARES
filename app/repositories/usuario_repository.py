from app.core.database import Database
from app.models.usuario import UsuarioCreate, UsuarioUpdate
from app.repositories.auth_repository import normalizar_nombre

class UsuarioRepository:
    def __init__(self):
        self.db = Database()

    def obtener_resumen(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.nombre AS rol, COUNT(*)::integer AS cantidad
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE u.estado IS TRUE AND r.estado IS TRUE
                GROUP BY r.id, r.nombre
                ORDER BY r.nombre;
            """)
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.nombre, u.correo, u.rol_id, r.nombre AS rol_nombre,
                       u.creado, u.actualizado, u.estado
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                ORDER BY u.id ASC;
            """)
            usuarios = cursor.fetchall()
            return usuarios
        except Exception as e:
            print(f"❌ Error al obtener usuarios: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, usuario_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.nombre, u.correo, u.rol_id, r.nombre AS rol_nombre,
                       u.creado, u.actualizado, u.estado
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE u.id = %s;
            """, (usuario_id,))
            usuario = cursor.fetchone()
            return usuario
        except Exception as e:
            print(f"❌ Error al obtener usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_nombre_rol(self, rol_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM rol WHERE id = %s AND estado IS TRUE;", (rol_id,))
            rol = cursor.fetchone()
            return rol["nombre"] if rol else None
        finally:
            if conn:
                conn.close()

    def usuario_tiene_rol(self, usuario_id: int, roles_permitidos: set[str]) -> bool:
        roles_normalizados = {normalizar_nombre(rol) for rol in roles_permitidos}
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.nombre
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE u.id = %s AND u.estado IS TRUE AND r.estado IS TRUE
                LIMIT 1;
            """, (usuario_id,))
            usuario = cursor.fetchone()
            return bool(usuario and normalizar_nombre(usuario["nombre"]) in roles_normalizados)
        finally:
            if conn:
                conn.close()

    def crear(
        self,
        usuario: UsuarioCreate,
        datos_estudiante: dict | None = None,
        datos_acudiente: dict | None = None,
    ):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO usuario (nombre, correo, password, rol_id, estado) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (
                usuario.nombre,
                usuario.correo,
                usuario.password,
                usuario.rol_id,
                usuario.estado,
            ))
            nuevo_id = cursor.fetchone()['id']
            if datos_estudiante is not None:
                cursor.execute("SELECT pg_advisory_xact_lock(4815162342);")
                cursor.execute(
                    """
                    SELECT COALESCE(
                        MAX(REGEXP_REPLACE(codigo_estudiante, '[^0-9]', '', 'g')::INTEGER),
                        0
                    ) + 1 AS siguiente
                    FROM estudiante
                    WHERE UPPER(codigo_estudiante) ~ '^EST[-_][0-9]+$';
                    """
                )
                siguiente_codigo = cursor.fetchone()["siguiente"]
                codigo_estudiante = f"EST-{siguiente_codigo:03d}"
                cursor.execute(
                    """
                    INSERT INTO estudiante (usuario_id, codigo_estudiante, grado, estado)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        nuevo_id,
                        codigo_estudiante,
                        datos_estudiante["grado"],
                        usuario.estado,
                    ),
                )
            if datos_acudiente is not None:
                cursor.execute(
                    """
                    INSERT INTO acudiente (usuario_id, documento, telefono, parentesco, estado)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        nuevo_id,
                        datos_acudiente["documento"],
                        datos_acudiente["telefono"],
                        datos_acudiente["parentesco"],
                        usuario.estado,
                    ),
                )
            conn.commit()
            return nuevo_id
        except Exception:
            if conn:
                conn.rollback()
            print("Error al crear usuario.")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, usuario_id: int, usuario: UsuarioUpdate):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            if usuario.password:
                cursor.execute("""
                    UPDATE usuario
                    SET nombre = %s, correo = %s, password = %s, rol_id = %s, estado = %s
                    WHERE id = %s
                    RETURNING id;
                """, (usuario.nombre, usuario.correo, usuario.password, usuario.rol_id, usuario.estado, usuario_id))
            else:
                cursor.execute("""
                    UPDATE usuario
                    SET nombre = %s, correo = %s, rol_id = %s, estado = %s
                    WHERE id = %s
                    RETURNING id;
                """, (usuario.nombre, usuario.correo, usuario.rol_id, usuario.estado, usuario_id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception:
            if conn:
                conn.rollback()
            print("Error al actualizar usuario.")
            raise
        finally:
            if conn:
                conn.close()
    def eliminar(self, usuario_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE usuario SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (usuario_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

