from app.core.database import Database
from app.models.asistencia import Asistencia
from psycopg2 import errors

class AsistenciaRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, u.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha,
                       COALESCE((
                           SELECT STRING_AGG(DISTINCT docente.nombre, ', ' ORDER BY docente.nombre)
                           FROM actividad_docente ad
                           JOIN usuario docente ON docente.id = ad.docente_id AND docente.estado IS TRUE
                           WHERE ad.actividad_id = actividad.id AND ad.estado IS TRUE
                       ), 'Sin docente asignado') AS docentes_asignados
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                JOIN actividad ON actividad.id = i.actividad_id
                ORDER BY a.id ASC;
            """)
            asistencias = cursor.fetchall()
            return asistencias
        except Exception as e:
            print(f"❌ Error al obtener asistencias: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_docente(self, usuario_id: int):
        """Devuelve asistencia únicamente de las actividades asignadas al docente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT a.*, u.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha,
                       COALESCE((
                           SELECT STRING_AGG(DISTINCT docente.nombre, ', ' ORDER BY docente.nombre)
                           FROM actividad_docente ad_asignada
                           JOIN usuario docente ON docente.id = ad_asignada.docente_id AND docente.estado IS TRUE
                           WHERE ad_asignada.actividad_id = actividad.id AND ad_asignada.estado IS TRUE
                       ), 'Sin docente asignado') AS docentes_asignados
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id
                JOIN actividad ON actividad.id = i.actividad_id
                JOIN actividad_docente ad ON ad.actividad_id = actividad.id AND ad.estado IS TRUE
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                WHERE ad.docente_id = %s AND a.estado IS TRUE
                  AND i.estado IS TRUE AND e.estado IS TRUE AND u.estado IS TRUE
                ORDER BY a.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener asistencia del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_resumen(self):
        """Resumen agregado para bienestar; no incluye nombres ni inscripciones."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)::integer AS cantidad
                FROM asistencia
                WHERE estado IS TRUE;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener el resumen de asistencia: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, asistencia_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM asistencia WHERE id = %s;", (asistencia_id,))
            asistencia = cursor.fetchone()
            return asistencia
        except Exception as e:
            print(f"❌ Error al obtener asistencia: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_usuario(self, usuario_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN actividad ON actividad.id = i.actividad_id
                WHERE e.usuario_id = %s AND a.estado IS TRUE
                ORDER BY a.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener las asistencias del usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_acudiente(self, usuario_id: int):
        """Devuelve asistencia activa de los acudidos y sus inscripciones activas."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT a.*, usuario.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id AND i.estado IS TRUE
                JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                JOIN usuario ON usuario.id = e.usuario_id AND usuario.estado IS TRUE
                JOIN actividad ON actividad.id = i.actividad_id
                JOIN acudiente_estudiante ae ON ae.estudiante_id = e.id
                JOIN acudiente ac ON ac.id = ae.acudiente_id AND ac.estado IS TRUE
                WHERE ac.usuario_id = %s AND a.estado IS TRUE
                ORDER BY actividad_fecha DESC, a.id DESC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener las asistencias de los acudidos: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_acudiente(self, asistencia_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id AND i.estado IS TRUE
                JOIN acudiente_estudiante ae ON ae.estudiante_id = i.estudiante_id
                JOIN acudiente ac ON ac.id = ae.acudiente_id AND ac.estado IS TRUE
                WHERE a.id = %s AND a.estado IS TRUE AND ac.usuario_id = %s
                LIMIT 1;
            """, (asistencia_id, usuario_id))
            return cursor.fetchone() is not None
        finally:
            if conn:
                conn.close()

    def pertenece_a_usuario(self, asistencia_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                WHERE a.id = %s AND e.usuario_id = %s AND a.estado IS TRUE
                LIMIT 1;
            """, (asistencia_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar la asistencia del usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_docente(self, asistencia_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM asistencia a
                JOIN inscripcion i ON i.id = a.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                JOIN actividad_docente ad ON ad.actividad_id = i.actividad_id AND ad.estado IS TRUE
                WHERE a.id = %s AND ad.docente_id = %s AND a.estado IS TRUE
                  AND i.estado IS TRUE AND e.estado IS TRUE AND u.estado IS TRUE
                LIMIT 1;
            """, (asistencia_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar asistencia del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def docente_puede_registrar(self, inscripcion_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM inscripcion i
                JOIN actividad_docente ad ON ad.actividad_id = i.actividad_id AND ad.estado IS TRUE
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                WHERE i.id = %s AND ad.docente_id = %s
                  AND i.estado IS TRUE AND e.estado IS TRUE AND u.estado IS TRUE
                LIMIT 1;
            """, (inscripcion_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar el roster del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, asistencia: Asistencia):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM asistencia WHERE inscripcion_id = %s LIMIT 1;", (asistencia.inscripcion_id,))
            if cursor.fetchone() is not None:
                raise ValueError("Ya existe un registro de asistencia para esta inscripción; edita el registro existente.")
            query = """
                INSERT INTO asistencia (inscripcion_id, asistio, observacion, nota, retroalimentacion, estado)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (
                asistencia.inscripcion_id, 
                asistencia.asistio, 
                asistencia.observacion,
                asistencia.nota,
                asistencia.retroalimentacion,
                asistencia.estado
            ))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except errors.UniqueViolation as e:
            if conn:
                conn.rollback()
            raise ValueError("Ya existe un registro de asistencia para esta inscripción.") from e
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear asistencia: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, asistencia_id: int, asistencia: Asistencia):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM asistencia
                WHERE inscripcion_id = %s AND id <> %s
                LIMIT 1;
            """, (asistencia.inscripcion_id, asistencia_id))
            if cursor.fetchone() is not None:
                raise ValueError("La inscripción ya tiene otro registro de asistencia.")
            query = """
                UPDATE asistencia 
                SET inscripcion_id = %s, asistio = %s, observacion = %s,
                    nota = %s, retroalimentacion = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (
                asistencia.inscripcion_id,
                asistencia.asistio,
                asistencia.observacion,
                asistencia.nota,
                asistencia.retroalimentacion,
                asistencia.estado,
                asistencia_id
            ))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except errors.UniqueViolation as e:
            if conn:
                conn.rollback()
            raise ValueError("La inscripción ya tiene otro registro de asistencia.") from e
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar asistencia: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, asistencia_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE asistencia SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (asistencia_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar asistencia: {e}")
            raise
        finally:
            if conn:
                conn.close()
