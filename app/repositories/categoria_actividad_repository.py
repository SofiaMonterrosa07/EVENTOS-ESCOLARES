from app.core.database import Database
from app.models.categoria_actividad import CategoriaActividad

class CategoriaActividadRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categoria_actividad ORDER BY id ASC;")
            categorias = cursor.fetchall()
            return categorias
        except Exception as e:
            print(f"❌ Error al obtener categorías: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, categoria_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categoria_actividad WHERE id = %s;", (categoria_id,))
            categoria = cursor.fetchone()
            return categoria
        except Exception as e:
            print(f"❌ Error al obtener categoría: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, categoria: CategoriaActividad):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO categoria_actividad (nombre, descripcion, estado) 
                VALUES (%s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (categoria.nombre, categoria.descripcion, categoria.estado))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear categoría: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, categoria_id: int, categoria: CategoriaActividad):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE categoria_actividad 
                SET nombre = %s, descripcion = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (categoria.nombre, categoria.descripcion, categoria.estado, categoria_id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar categoría: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, categoria_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE categoria_actividad SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (categoria_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar categoría: {e}")
            raise
        finally:
            if conn:
                conn.close()