from app.core.database import Database
from app.models.modulo import Modulo

class ModuloRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM modulo ORDER BY id ASC;")
            modulos = cursor.fetchall()
            return modulos
        except Exception as e:
            print(f"❌ Error al obtener módulos: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, modulo_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM modulo WHERE id = %s;", (modulo_id,))
            modulo = cursor.fetchone()
            return modulo
        except Exception as e:
            print(f"❌ Error al obtener módulo: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, modulo: Modulo):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO modulo (nombre, descripcion, estado) 
                VALUES (%s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (modulo.nombre, modulo.descripcion, modulo.estado))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear módulo: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, modulo_id: int, modulo: Modulo):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE modulo 
                SET nombre = %s, descripcion = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (modulo.nombre, modulo.descripcion, modulo.estado, modulo_id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar módulo: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, modulo_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE modulo SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (modulo_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar módulo: {e}")
            raise
        finally:
            if conn:
                conn.close()