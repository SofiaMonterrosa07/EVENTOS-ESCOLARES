from app.core.database import Database
from app.models.estudiante import Estudiante

class EstudianteRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, u.nombre AS usuario_nombre
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                ORDER BY e.id ASC;
            """)
            estudiantes = cursor.fetchall()
            return estudiantes
        except Exception as e:
            print(f"❌ Error al obtener estudiantes: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_para_inscripciones(self):
        """Lista mínima para que coordinación asigne una inscripción sin ver otros datos de cuenta."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.usuario_id, e.codigo_estudiante, e.grado, e.estado,
                       u.nombre AS usuario_nombre
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.estado IS TRUE AND u.estado IS TRUE
                ORDER BY u.nombre ASC;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener estudiantes para inscripciones: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_usuario(self, usuario_id: int):
        """Perfil escolar del estudiante autenticado, sin datos de cuenta."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.codigo_estudiante, e.grado, e.estado
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.usuario_id = %s AND u.estado IS TRUE
                ORDER BY e.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def obtener_por_acudiente(self, usuario_id: int):
        """Estudiantes vinculados directamente al acudiente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT e.id, e.codigo_estudiante, e.grado, e.estado,
                       u.nombre AS usuario_nombre
                FROM acudiente_estudiante ae
                JOIN acudiente ac ON ac.id = ae.acudiente_id
                JOIN estudiante e ON e.id = ae.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                WHERE ac.usuario_id = %s AND ac.estado IS TRUE
                  AND u.estado IS TRUE
                ORDER BY e.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def obtener_por_docente(self, usuario_id: int):
        """Roster mínimo limitado a inscripciones activas de sus actividades."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT e.id, e.codigo_estudiante, e.grado, e.estado,
                       u.nombre AS usuario_nombre, a.id AS actividad_id,
                       a.nombre AS actividad_nombre
                FROM actividad_docente ad
                JOIN actividad a ON a.id = ad.actividad_id
                JOIN inscripcion i ON i.actividad_id = a.id AND i.estado IS TRUE
                JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                JOIN usuario u ON u.id = e.usuario_id AND u.estado IS TRUE
                WHERE ad.docente_id = %s AND ad.estado IS TRUE
                ORDER BY a.nombre, u.nombre;
            """, (usuario_id,))
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def pertenece_a_usuario(self, estudiante_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.id = %s AND e.usuario_id = %s AND u.estado IS TRUE
                LIMIT 1;
            """, (estudiante_id, usuario_id))
            return cursor.fetchone() is not None
        finally:
            if conn:
                conn.close()

    def pertenece_a_acudiente(self, estudiante_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM acudiente_estudiante ae
                JOIN acudiente ac ON ac.id = ae.acudiente_id
                WHERE ae.estudiante_id = %s AND ac.usuario_id = %s
                  AND ac.estado IS TRUE
                LIMIT 1;
            """, (estudiante_id, usuario_id))
            return cursor.fetchone() is not None
        finally:
            if conn:
                conn.close()

    def obtener_acudientes_vinculados(self, estudiante_id: int):
        """Acudientes activos asociados al estudiante, con su parentesco."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ac.id AS acudiente_id, u.nombre AS acudiente_nombre,
                       ae.parentesco
                FROM acudiente_estudiante ae
                JOIN acudiente ac ON ac.id = ae.acudiente_id
                JOIN usuario u ON u.id = ac.usuario_id
                WHERE ae.estudiante_id = %s
                  AND ac.estado IS TRUE AND u.estado IS TRUE
                ORDER BY u.nombre ASC;
            """, (estudiante_id,))
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def reemplazar_acudientes_vinculados(self, estudiante_id: int, vinculos: list):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.id = %s AND e.estado IS TRUE AND u.estado IS TRUE
                FOR UPDATE OF e;
            """, (estudiante_id,))
            if cursor.fetchone() is None:
                raise ValueError("No se encontró un estudiante activo.")

            ids = [vinculo.acudiente_id for vinculo in vinculos]
            if len(ids) != len(set(ids)):
                raise ValueError("No repitas el mismo acudiente en la lista.")
            if ids:
                cursor.execute("""
                    SELECT a.id
                    FROM acudiente a
                    JOIN usuario u ON u.id = a.usuario_id
                    WHERE a.id = ANY(%s) AND a.estado IS TRUE AND u.estado IS TRUE;
                """, (ids,))
                ids_activos = {fila["id"] for fila in cursor.fetchall()}
                if ids_activos != set(ids):
                    raise ValueError("Selecciona únicamente acudientes activos.")

            cursor.execute("DELETE FROM acudiente_estudiante WHERE estudiante_id = %s;", (estudiante_id,))
            for vinculo in vinculos:
                parentesco = (vinculo.parentesco or "").strip() or None
                cursor.execute("""
                    INSERT INTO acudiente_estudiante (acudiente_id, estudiante_id, parentesco)
                    VALUES (%s, %s, %s);
                """, (vinculo.acudiente_id, estudiante_id, parentesco))
            conn.commit()
            return len(vinculos)
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_docente(self, estudiante_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM actividad_docente ad
                JOIN inscripcion i ON i.actividad_id = ad.actividad_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.id = %s AND ad.docente_id = %s
                  AND ad.estado IS TRUE AND i.estado IS TRUE
                  AND e.estado IS TRUE AND u.estado IS TRUE
                LIMIT 1;
            """, (estudiante_id, usuario_id))
            return cursor.fetchone() is not None
        finally:
            if conn:
                conn.close()

    def obtener_referencia(self, estudiante_id: int):
        """Campos mínimos para coordinación y usuarios con relación comprobada."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.codigo_estudiante, e.grado, e.estado,
                       u.nombre AS usuario_nombre
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.id = %s;
            """, (estudiante_id,))
            return cursor.fetchone()
        finally:
            if conn:
                conn.close()

    def obtener_resumen_bienestar(self):
        """Total agregado para seguimiento institucional sin identificar estudiantes."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)::integer AS cantidad
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.estado IS TRUE AND u.estado IS TRUE;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener el resumen de estudiantes: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, estudiante_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM estudiante WHERE id = %s;", (estudiante_id,))
            estudiante = cursor.fetchone()
            return estudiante
        except Exception as e:
            print(f"❌ Error al obtener estudiante: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, estudiante: Estudiante):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO estudiante (usuario_id, codigo_estudiante, grado, estado) 
                VALUES (%s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (estudiante.usuario_id, estudiante.codigo_estudiante, estudiante.grado, estudiante.estado))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear estudiante: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, estudiante_id: int, estudiante: Estudiante):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE estudiante 
                SET usuario_id = %s, codigo_estudiante = %s, grado = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (estudiante.usuario_id, estudiante.codigo_estudiante, estudiante.grado, estudiante.estado, estudiante_id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar estudiante: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, estudiante_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE estudiante SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (estudiante_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar estudiante: {e}")
            raise
        finally:
            if conn:
                conn.close()
