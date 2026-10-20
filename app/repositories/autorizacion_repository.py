from app.core.database import Database
from app.models.autorizacion import Autorizacion
from datetime import date

class AutorizacionRepository:
    def __init__(self):
        self.db = Database()

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autorizacion ORDER BY id ASC;")
            autorizaciones = cursor.fetchall()
            return autorizaciones
        except Exception as e:
            print(f"❌ Error al obtener autorizaciones: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_resumen(self):
        """Devuelve solo el total de autorizaciones para tarjetas de analítica."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*)::integer AS cantidad FROM autorizacion;")
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener el resumen de autorizaciones: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_acudiente(self, usuario_id: int):
        """Devuelve autorizaciones relacionadas con la cuenta del acudiente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT au.id, au.inscripcion_id, au.acudiente_id, au.estado,
                       au.fecha_autorizacion, au.creado, au.actualizado,
                       usuario.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM autorizacion au
                JOIN acudiente ac ON ac.id = au.acudiente_id
                JOIN inscripcion i ON i.id = au.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario ON usuario.id = e.usuario_id
                JOIN actividad ON actividad.id = i.actividad_id
                WHERE ac.usuario_id = %s AND ac.estado IS TRUE
                ORDER BY au.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener autorizaciones del acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_estudiante(self, usuario_id: int):
        """Devuelve solo el estado y la actividad de las autorizaciones propias."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT au.id, au.inscripcion_id, au.estado, au.fecha_autorizacion,
                       au.creado, au.actualizado,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM autorizacion au
                JOIN inscripcion i ON i.id = au.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN actividad ON actividad.id = i.actividad_id
                WHERE e.usuario_id = %s AND e.estado IS TRUE
                ORDER BY actividad.fecha DESC, au.id DESC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener autorizaciones propias del estudiante: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, autorizacion_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autorizacion WHERE id = %s;", (autorizacion_id,))
            autorizacion = cursor.fetchone()
            return autorizacion
        except Exception as e:
            print(f"❌ Error al obtener autorización: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_acudiente(self, autorizacion_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM autorizacion au
                JOIN acudiente ac ON ac.id = au.acudiente_id
                WHERE au.id = %s AND ac.usuario_id = %s AND ac.estado IS TRUE
                LIMIT 1;
            """, (autorizacion_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar pertenencia de autorización: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id_para_estudiante(self, autorizacion_id: int, usuario_id: int):
        """Busca una autorización propia y omite la identidad del acudiente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT au.id, au.inscripcion_id, au.estado, au.fecha_autorizacion,
                       au.creado, au.actualizado,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM autorizacion au
                JOIN inscripcion i ON i.id = au.inscripcion_id
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN actividad ON actividad.id = i.actividad_id
                WHERE au.id = %s AND e.usuario_id = %s AND e.estado IS TRUE
                LIMIT 1;
            """, (autorizacion_id, usuario_id))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error al validar autorización propia del estudiante: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar_respuesta_acudiente(self, autorizacion_id: int, usuario_id: int, estado: bool):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE autorizacion au
                SET estado = %s, fecha_autorizacion = CURRENT_DATE
                WHERE au.id = %s
                  AND EXISTS (
                      SELECT 1
                      FROM acudiente ac
                      WHERE ac.id = au.acudiente_id
                        AND ac.usuario_id = %s
                        AND ac.estado IS TRUE
                  )
                RETURNING au.id;
            """, (estado, autorizacion_id, usuario_id))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error al registrar la respuesta del acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, autorizacion: Autorizacion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            fecha_actual = (
                date.fromisoformat(autorizacion.fecha_autorizacion)
                if autorizacion.estado and autorizacion.fecha_autorizacion
                else date.today() if autorizacion.estado else None
            )
            query = """
                INSERT INTO autorizacion (inscripcion_id, acudiente_id, estado, fecha_autorizacion) 
                VALUES (%s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (
                autorizacion.inscripcion_id, 
                autorizacion.acudiente_id, 
                autorizacion.estado,
                fecha_actual
            ))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear autorización: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ✅ CORREGIDO: Ahora incluye fecha_autorizacion
    def actualizar(self, autorizacion_id: int, autorizacion: Autorizacion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE autorizacion 
                SET inscripcion_id = %s, acudiente_id = %s, estado = %s, fecha_autorizacion = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (
                autorizacion.inscripcion_id, 
                autorizacion.acudiente_id, 
                autorizacion.estado,
                autorizacion.fecha_autorizacion,
                autorizacion_id
            ))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar autorización: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, autorizacion_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE autorizacion SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (autorizacion_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar autorización: {e}")
            raise
        finally:
            if conn:
                conn.close()
