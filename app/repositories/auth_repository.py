import unicodedata

from app.core.database import Database


def normalizar_nombre(valor: str) -> str:
    return "".join(
        letra for letra in unicodedata.normalize("NFD", str(valor or "").strip().lower())
        if unicodedata.category(letra) != "Mn"
    )


class AuthRepository:
    def __init__(self):
        self.db = Database()

    def obtener_roles_activos(self):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre FROM rol WHERE estado IS TRUE ORDER BY nombre ASC;")
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def buscar_usuario_para_login(self, correo: str, rol_id: int):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.nombre, u.correo, u.password, u.rol_id, u.estado,
                       r.nombre AS rol_nombre, r.estado AS rol_estado
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE LOWER(TRIM(u.correo)) = LOWER(TRIM(%s)) AND u.rol_id = %s
                LIMIT 1;
                """,
                (correo, rol_id),
            )
            return cursor.fetchone()
        finally:
            if conn:
                conn.close()

    def obtener_principal(self, usuario_id: int):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.nombre, u.correo, u.rol_id, u.estado,
                       r.nombre AS rol_nombre, r.estado AS rol_estado
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE u.id = %s
                LIMIT 1;
                """,
                (usuario_id,),
            )
            return cursor.fetchone()
        finally:
            if conn:
                conn.close()

    def obtener_perfil(self, usuario_id: int):
        principal = self.obtener_principal(usuario_id)
        if not principal:
            return None

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.id, m.nombre
                FROM modulo_rol mr
                JOIN modulo m ON m.id = mr.modulo_id
                WHERE mr.rol_id = %s AND mr.estado IS TRUE AND m.estado IS TRUE
                ORDER BY m.nombre ASC;
                """,
                (principal["rol_id"],),
            )
            modulos = cursor.fetchall()
        finally:
            if conn:
                conn.close()

        return {
            "usuario": {
                "id": principal["id"],
                "nombre": principal["nombre"],
                "correo": principal["correo"],
            },
            "rol": {
                "id": principal["rol_id"],
                "nombre": principal["rol_nombre"],
            },
            "modulos": modulos,
        }

    def actualizar_password(self, usuario_id: int, password_hash: str, hash_anterior: str):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE usuario SET password = %s WHERE id = %s AND password = %s RETURNING id;",
                (password_hash, usuario_id, hash_anterior),
            )
            actualizado = cursor.fetchone() is not None
            conn.commit()
            return actualizado
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def tiene_modulo_activo(self, rol_id: int, nombres_modulo: tuple[str, ...]) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.nombre
                FROM modulo_rol mr
                JOIN modulo m ON m.id = mr.modulo_id
                WHERE mr.rol_id = %s AND mr.estado IS TRUE AND m.estado IS TRUE;
                """,
                (rol_id,),
            )
            permitidos = {normalizar_nombre(fila["nombre"]) for fila in cursor.fetchall()}
            return any(normalizar_nombre(nombre) in permitidos for nombre in nombres_modulo)
        finally:
            if conn:
                conn.close()
