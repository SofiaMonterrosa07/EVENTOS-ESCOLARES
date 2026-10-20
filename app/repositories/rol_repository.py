from app.core.database import Database
from app.models.rol import Rol

class RolRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rol ORDER BY id ASC;")
            roles = cursor.fetchall()
            return roles
        except Exception as e:
            print(f"❌ Error al obtener roles: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, rol_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rol WHERE id = %s;", (rol_id,))
            rol = cursor.fetchone()
            return rol
        except Exception as e:
            print(f"❌ Error al obtener rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, rol: Rol):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO rol (nombre, descripcion, estado) 
                VALUES (%s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (rol.nombre, rol.descripcion, rol.estado))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, rol_id: int, rol: Rol):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE rol 
                SET nombre = %s, descripcion = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (rol.nombre, rol.descripcion, rol.estado, rol_id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, rol_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE rol SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (rol_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar rol: {e}")
            raise
        finally:
            if conn:
                conn.close()