from app.core.database import Database
from app.models.acudiente import Acudiente

class AcudienteRepository:
    def __init__(self):
        self.db = Database()

    def obtener_resumen(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)::integer AS cantidad
                FROM acudiente a
                JOIN usuario u ON u.id = a.usuario_id
                WHERE a.estado IS TRUE AND u.estado IS TRUE;
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
                SELECT a.*, u.nombre AS usuario_nombre
                FROM acudiente a
                JOIN usuario u ON u.id = a.usuario_id
                ORDER BY a.id ASC;
            """)
            acudientes = cursor.fetchall()
            return acudientes
        except Exception as e:
            print(f"❌ Error al obtener acudientes: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_para_autorizacion(self):
        """Lista mínima de acudientes para que coordinación vincule una autorización."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.usuario_id, a.parentesco, a.estado,
                       u.nombre AS usuario_nombre
                FROM acudiente a
                JOIN usuario u ON u.id = a.usuario_id
                WHERE a.estado IS TRUE AND u.estado IS TRUE
                ORDER BY u.nombre ASC;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener acudientes para autorizaciones: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_estudiantes_vinculados(self, acudiente_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id AS estudiante_id, e.codigo_estudiante, e.grado,
                       u.nombre AS estudiante_nombre, ae.parentesco
                FROM acudiente_estudiante ae
                JOIN estudiante e ON e.id = ae.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                WHERE ae.acudiente_id = %s AND e.estado IS TRUE AND u.estado IS TRUE
                ORDER BY u.nombre ASC, e.id ASC;
            """, (acudiente_id,))
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def reemplazar_estudiantes_vinculados(self, acudiente_id: int, vinculos: list):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id
                FROM acudiente a
                JOIN usuario u ON u.id = a.usuario_id
                WHERE a.id = %s AND a.estado IS TRUE AND u.estado IS TRUE
                FOR UPDATE OF a;
            """, (acudiente_id,))
            if cursor.fetchone() is None:
                raise ValueError("No se encontró un acudiente activo.")

            ids = [vinculo.estudiante_id for vinculo in vinculos]
            if len(ids) != len(set(ids)):
                raise ValueError("No repitas el mismo estudiante en la lista.")
            if ids:
                cursor.execute("""
                    SELECT e.id
                    FROM estudiante e
                    JOIN usuario u ON u.id = e.usuario_id
                    WHERE e.id = ANY(%s) AND e.estado IS TRUE AND u.estado IS TRUE;
                """, (ids,))
                ids_activos = {fila["id"] for fila in cursor.fetchall()}
                if ids_activos != set(ids):
                    raise ValueError("Selecciona únicamente estudiantes activos.")

            cursor.execute("DELETE FROM acudiente_estudiante WHERE acudiente_id = %s;", (acudiente_id,))
            for vinculo in vinculos:
                parentesco = (vinculo.parentesco or "").strip() or None
                cursor.execute("""
                    INSERT INTO acudiente_estudiante (acudiente_id, estudiante_id, parentesco)
                    VALUES (%s, %s, %s);
                """, (acudiente_id, vinculo.estudiante_id, parentesco))
            conn.commit()
            return len(vinculos)
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, acudiente_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM acudiente WHERE id = %s;", (acudiente_id,))
            acudiente = cursor.fetchone()
            return acudiente
        except Exception as e:
            print(f"❌ Error al obtener acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_usuario(self, usuario_id: int):
        """Ficha del acudiente autenticado; no devuelve la relación con otros usuarios."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, documento, telefono, parentesco, estado
                FROM acudiente
                WHERE usuario_id = %s
                LIMIT 1;
            """, (usuario_id,))
            return cursor.fetchone()
        finally:
            if conn:
                conn.close()

    def pertenece_a_usuario(self, acudiente_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM acudiente
                WHERE id = %s AND usuario_id = %s AND estado IS TRUE
                LIMIT 1;
            """, (acudiente_id, usuario_id))
            return cursor.fetchone() is not None
        finally:
            if conn:
                conn.close()

    def obtener_referencia(self, acudiente_id: int):
        """Datos mínimos de referencia para coordinación."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.parentesco, a.estado, u.nombre AS usuario_nombre
                FROM acudiente a
                JOIN usuario u ON u.id = a.usuario_id
                WHERE a.id = %s;
            """, (acudiente_id,))
            return cursor.fetchone()
        finally:
            if conn:
                conn.close()

    def crear(self, acudiente: Acudiente):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO acudiente (usuario_id, documento, telefono, parentesco, estado) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (
                acudiente.usuario_id,
                acudiente.documento,
                acudiente.telefono,
                acudiente.parentesco, acudiente.estado
            ))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, acudiente_id: int, acudiente: Acudiente):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE acudiente 
                SET usuario_id = %s, documento = %s, telefono = %s, parentesco = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (
                acudiente.usuario_id,
                acudiente.documento,
                acudiente.telefono,
                acudiente.parentesco,
                acudiente.estado,
                acudiente_id
            ))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, acudiente_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE acudiente SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (acudiente_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()
