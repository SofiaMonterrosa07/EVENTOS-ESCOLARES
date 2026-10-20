from app.core.database import Database
from app.models.modulo_rol import ModuloRol

class ModuloRolRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM modulo_rol ORDER BY id ASC;")
            registros = cursor.fetchall()
            return registros
        except Exception as e:
            print(f"❌ Error al obtener relaciones módulo-rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM modulo_rol WHERE id = %s;", (id,))
            registro = cursor.fetchone()
            return registro
        except Exception as e:
            print(f"❌ Error al obtener relación módulo-rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, data: ModuloRol):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO modulo_rol (rol_id, modulo_id, estado) 
                VALUES (%s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (data.rol_id, data.modulo_id, data.estado))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear relación módulo-rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, id: int, data: ModuloRol):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE modulo_rol 
                SET rol_id = %s, modulo_id = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (data.rol_id, data.modulo_id, data.estado, id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar relación módulo-rol: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE modulo_rol SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar relación módulo-rol: {e}")
            raise
        finally:
            if conn:
                conn.close()
