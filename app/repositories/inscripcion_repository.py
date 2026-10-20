from app.core.database import Database
from app.models.inscripcion import Inscripcion
from datetime import date
from psycopg2 import errors

class InscripcionRepository:
    def __init__(self):
        self.db = Database()

    def _validar_inscripcion(self, cursor, estudiante_id: int, actividad_id: int, excluir_id: int | None = None):
        """Valida la elegibilidad y bloquea la actividad mientras comprueba cupos."""
        cursor.execute("""
            SELECT e.id
            FROM estudiante e
            JOIN usuario u ON u.id = e.usuario_id
            WHERE e.id = %s AND e.estado IS TRUE AND u.estado IS TRUE
            FOR SHARE OF e, u;
        """, (estudiante_id,))
        if cursor.fetchone() is None:
            raise ValueError("El estudiante no está activo o no existe.")

        cursor.execute("""
            SELECT id, cupo, fecha, estado
            FROM actividad
            WHERE id = %s
            FOR UPDATE;
        """, (actividad_id,))
        actividad = cursor.fetchone()
        if not actividad:
            raise ValueError("La actividad no existe.")
        if not actividad["estado"]:
            raise ValueError("No se puede inscribir en una actividad inactiva.")
        cursor.execute("SELECT CURRENT_DATE AS hoy;")
        hoy = cursor.fetchone()["hoy"]
        if actividad["fecha"] < hoy:
            raise ValueError("No se puede inscribir en una actividad finalizada.")

        filtro_exclusion = "" if excluir_id is None else " AND id <> %s"
        parametros_duplicado = (estudiante_id, actividad_id) if excluir_id is None else (
            estudiante_id, actividad_id, excluir_id
        )
        cursor.execute(f"""
            SELECT 1
            FROM inscripcion
            WHERE estudiante_id = %s AND actividad_id = %s{filtro_exclusion}
            LIMIT 1;
        """, parametros_duplicado)
        if cursor.fetchone() is not None:
            raise ValueError("El estudiante ya tiene un registro de inscripción para esta actividad.")

        filtro_conteo = "" if excluir_id is None else " AND i.id <> %s"
        parametros_conteo = (actividad_id,) if excluir_id is None else (actividad_id, excluir_id)
        cursor.execute(f"""
            SELECT COUNT(*)::integer AS cantidad
            FROM inscripcion i
            JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
            JOIN usuario u ON u.id = e.usuario_id AND u.estado IS TRUE
            WHERE i.actividad_id = %s AND i.estado IS TRUE
              {filtro_conteo};
        """, parametros_conteo)
        ocupados = int(cursor.fetchone()["cantidad"])
        if ocupados >= int(actividad["cupo"]):
            raise ValueError("La actividad no tiene cupos disponibles.")
        return hoy

    def _crear_en_inscripcion(self, cursor, estudiante_id: int, actividad_id: int, fecha_inscripcion: date | None, estado: bool):
        hoy = self._validar_inscripcion(cursor, estudiante_id, actividad_id)
        if fecha_inscripcion is not None and fecha_inscripcion != hoy:
            raise ValueError("La fecha de inscripción la asigna el sistema y no se puede modificar.")
        cursor.execute("""
            INSERT INTO inscripcion (estudiante_id, actividad_id, fecha_inscripcion, estado)
            VALUES (%s, %s, %s, %s) RETURNING id;
        """, (estudiante_id, actividad_id, hoy, estado))
        return int(cursor.fetchone()["id"])

    def crear_para_usuario(self, usuario_id: int, actividad_id: int) -> int:
        """Inscripción propia del estudiante autenticado."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id
                FROM estudiante e
                JOIN usuario u ON u.id = e.usuario_id
                WHERE e.usuario_id = %s AND e.estado IS TRUE AND u.estado IS TRUE
                FOR SHARE OF e, u;
            """, (usuario_id,))
            estudiante = cursor.fetchone()
            if not estudiante:
                raise ValueError("No se encontró un perfil de estudiante activo para esta cuenta.")
            nuevo_id = self._crear_en_inscripcion(cursor, int(estudiante["id"]), actividad_id, None, True)
            conn.commit()
            return nuevo_id
        except errors.UniqueViolation as error:
            if conn:
                conn.rollback()
            raise ValueError("Ya existe un registro de inscripción para ese estudiante y actividad.") from error
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def crear_para_acudido(self, usuario_acudiente_id: int, estudiante_id: int, actividad_id: int) -> int:
        """Inscripción de un estudiante previamente vinculado al acudiente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ac.id
                FROM acudiente ac
                JOIN usuario u ON u.id = ac.usuario_id
                WHERE ac.usuario_id = %s AND ac.estado IS TRUE AND u.estado IS TRUE
                LIMIT 1
                FOR SHARE OF ac, u;
            """, (usuario_acudiente_id,))
            acudiente = cursor.fetchone()
            if not acudiente:
                raise ValueError("No se encontró un perfil de acudiente activo para esta cuenta.")
            acudiente_id = int(acudiente["id"])
            cursor.execute("""
                SELECT 1
                FROM acudiente_estudiante ae
                WHERE ae.acudiente_id = %s AND ae.estudiante_id = %s
                LIMIT 1;
            """, (acudiente_id, estudiante_id))
            if cursor.fetchone() is None:
                raise ValueError("El estudiante no está vinculado a este acudiente.")

            inscripcion_id = self._crear_en_inscripcion(cursor, estudiante_id, actividad_id, None, True)
            # Una solicitud del acudiente crea una autorización pendiente para esta inscripción.
            cursor.execute("""
                INSERT INTO autorizacion (inscripcion_id, acudiente_id, estado, fecha_autorizacion)
                VALUES (%s, %s, FALSE, NULL);
            """, (inscripcion_id, acudiente_id))
            conn.commit()
            return inscripcion_id
        except errors.UniqueViolation as error:
            if conn:
                conn.rollback()
            raise ValueError("Ya existe un registro de inscripción para ese estudiante y actividad.") from error
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def cancelar_para_usuario(self, inscripcion_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inscripcion i
                SET estado = FALSE, actualizado = CURRENT_TIMESTAMP
                FROM actividad a, estudiante e
                WHERE i.id = %s AND i.estado IS TRUE
                  AND a.id = i.actividad_id AND e.id = i.estudiante_id
                  AND e.usuario_id = %s
                  AND (a.fecha > CURRENT_DATE OR (a.fecha = CURRENT_DATE AND a.hora > CURRENT_TIME))
                RETURNING i.id;
            """, (inscripcion_id, usuario_id))
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

    def cancelar_para_acudiente(self, inscripcion_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inscripcion i
                SET estado = FALSE, actualizado = CURRENT_TIMESTAMP
                FROM actividad a
                WHERE i.id = %s AND i.estado IS TRUE
                  AND a.id = i.actividad_id
                  AND (a.fecha > CURRENT_DATE OR (a.fecha = CURRENT_DATE AND a.hora > CURRENT_TIME))
                  AND EXISTS (
                      SELECT 1
                      FROM acudiente_estudiante ae
                      JOIN acudiente ac ON ac.id = ae.acudiente_id
                      WHERE ae.estudiante_id = i.estudiante_id
                        AND ac.usuario_id = %s AND ac.estado IS TRUE
                  )
                RETURNING i.id;
            """, (inscripcion_id, usuario_id))
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

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.id, i.estudiante_id, i.actividad_id, i.fecha_inscripcion,
                       i.estado, i.creado, i.actualizado,
                       u.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha,
                       COALESCE((
                           SELECT STRING_AGG(DISTINCT docente.nombre, ', ' ORDER BY docente.nombre)
                           FROM actividad_docente ad
                           JOIN usuario docente ON docente.id = ad.docente_id AND docente.estado IS TRUE
                           WHERE ad.actividad_id = actividad.id AND ad.estado IS TRUE
                       ), 'Sin docente asignado') AS docentes_asignados
                FROM inscripcion i
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                JOIN actividad ON actividad.id = i.actividad_id
                ORDER BY i.id ASC;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Error al obtener inscripciones: {e}")
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
                SELECT i.id, i.estudiante_id, i.actividad_id, i.fecha_inscripcion,
                       i.estado, i.creado, i.actualizado
                FROM inscripcion i
                JOIN estudiante e ON e.id = i.estudiante_id
                WHERE e.usuario_id = %s
                ORDER BY i.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener las inscripciones del usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_acudiente(self, usuario_id: int):
        """Devuelve inscripciones de estudiantes vinculados directamente al acudiente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT i.id, i.estudiante_id, i.actividad_id,
                       i.fecha_inscripcion, i.estado, i.creado, i.actualizado,
                       usuario.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM inscripcion i
                JOIN estudiante ON estudiante.id = i.estudiante_id
                JOIN acudiente_estudiante ae ON ae.estudiante_id = estudiante.id
                JOIN acudiente ac ON ac.id = ae.acudiente_id
                JOIN usuario ON usuario.id = estudiante.usuario_id
                JOIN actividad ON actividad.id = i.actividad_id
                WHERE ac.usuario_id = %s AND ac.estado IS TRUE
                ORDER BY i.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener las inscripciones del acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_docente(self, usuario_id: int):
        """Devuelve solo el roster de las actividades asignadas al docente."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT i.id, i.estudiante_id, i.actividad_id,
                       i.fecha_inscripcion, i.estado, i.creado, i.actualizado,
                       u.nombre AS estudiante_nombre,
                       actividad.nombre AS actividad_nombre,
                       actividad.fecha AS actividad_fecha
                FROM inscripcion i
                JOIN actividad ON actividad.id = i.actividad_id
                JOIN actividad_docente ad ON ad.actividad_id = actividad.id AND ad.estado IS TRUE
                JOIN estudiante e ON e.id = i.estudiante_id
                JOIN usuario u ON u.id = e.usuario_id
                WHERE ad.docente_id = %s
                  AND i.estado IS TRUE AND e.estado IS TRUE AND u.estado IS TRUE
                ORDER BY i.id ASC;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener las inscripciones del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_usuario(self, inscripcion_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM inscripcion i
                JOIN estudiante e ON e.id = i.estudiante_id
                WHERE i.id = %s AND e.usuario_id = %s
                LIMIT 1;
            """, (inscripcion_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar la inscripción del usuario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_acudiente(self, inscripcion_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM inscripcion i
                JOIN acudiente_estudiante ae ON ae.estudiante_id = i.estudiante_id
                JOIN acudiente ac ON ac.id = ae.acudiente_id
                WHERE i.id = %s AND ac.usuario_id = %s AND ac.estado IS TRUE
                LIMIT 1;
            """, (inscripcion_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar la inscripcion del acudiente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_docente(self, inscripcion_id: int, usuario_id: int) -> bool:
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
            print(f"Error al validar la inscripción del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def resumen_actividades(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id AS actividad_id,
                       COUNT(i.id) FILTER (WHERE e.id IS NOT NULL AND u.id IS NOT NULL)::integer AS inscritos
                FROM actividad a
                LEFT JOIN inscripcion i ON i.actividad_id = a.id AND i.estado IS TRUE
                LEFT JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                LEFT JOIN usuario u ON u.id = e.usuario_id AND u.estado IS TRUE
                WHERE a.estado IS TRUE AND a.fecha >= CURRENT_DATE
                GROUP BY a.id;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener el resumen de cupos: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def resumen_institucional_actividades(self):
        """Devuelve conteos por actividad para reportes, sin datos de estudiantes ni IDs."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT actividad.nombre AS nombre,
                       actividad.fecha AS fecha,
                       COALESCE(categoria.nombre, 'Sin categoría') AS tipo,
                       actividad.cupo AS cupos,
                       COUNT(DISTINCT i.id) FILTER (
                           WHERE i.estado IS TRUE AND e.id IS NOT NULL AND u.id IS NOT NULL
                       )::integer AS inscritos,
                       COUNT(DISTINCT i.id) FILTER (
                           WHERE i.estado IS TRUE AND e.id IS NOT NULL AND u.id IS NOT NULL AND EXISTS (
                               SELECT 1 FROM autorizacion au
                               WHERE au.inscripcion_id = i.id AND au.estado IS TRUE
                           )
                       )::integer AS autorizadas,
                       COUNT(DISTINCT i.id) FILTER (
                           WHERE i.estado IS TRUE AND e.id IS NOT NULL AND u.id IS NOT NULL
                             AND NOT EXISTS (
                                 SELECT 1 FROM autorizacion au
                                 WHERE au.inscripcion_id = i.id AND au.estado IS TRUE
                             )
                             AND EXISTS (
                                 SELECT 1 FROM autorizacion au
                                 WHERE au.inscripcion_id = i.id
                                   AND au.estado IS FALSE
                                   AND au.fecha_autorizacion IS NOT NULL
                             )
                       )::integer AS rechazadas,
                       COUNT(DISTINCT i.id) FILTER (
                           WHERE i.estado IS TRUE AND e.id IS NOT NULL AND u.id IS NOT NULL
                             AND NOT EXISTS (
                                 SELECT 1 FROM autorizacion au
                                 WHERE au.inscripcion_id = i.id AND au.fecha_autorizacion IS NOT NULL
                             )
                       )::integer AS pendientes
                FROM actividad
                LEFT JOIN categoria_actividad categoria ON categoria.id = actividad.categoria_id
                LEFT JOIN inscripcion i ON i.actividad_id = actividad.id
                LEFT JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                LEFT JOIN usuario u ON u.id = e.usuario_id AND u.estado IS TRUE
                WHERE actividad.estado IS TRUE
                GROUP BY actividad.id, actividad.nombre, actividad.fecha,
                         categoria.nombre, actividad.cupo
                ORDER BY actividad.fecha, actividad.nombre;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener el reporte agregado de actividades: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_id(self, inscripcion_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, estudiante_id, actividad_id, fecha_inscripcion, estado, creado, actualizado
                FROM inscripcion
                WHERE id = %s;
            """, (inscripcion_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"❌ Error al obtener inscripción: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def crear(self, inscripcion: Inscripcion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            nuevo_id = self._crear_en_inscripcion(
                cursor,
                inscripcion.estudiante_id,
                inscripcion.actividad_id,
                inscripcion.fecha_inscripcion,
                inscripcion.estado,
            )
            conn.commit()
            return nuevo_id
        except errors.UniqueViolation as e:
            if conn:
                conn.rollback()
            raise ValueError("Ya existe un registro de inscripción para ese estudiante y actividad.") from e
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear inscripción: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def actualizar(self, inscripcion_id: int, inscripcion: Inscripcion):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            if inscripcion.estado:
                self._validar_inscripcion(
                    cursor, inscripcion.estudiante_id, inscripcion.actividad_id, excluir_id=inscripcion_id
                )
            cursor.execute("""
                UPDATE inscripcion
                SET estudiante_id = %s, actividad_id = %s, estado = %s
                WHERE id = %s RETURNING id;
            """, (
                inscripcion.estudiante_id,
                inscripcion.actividad_id,
                inscripcion.estado,
                inscripcion_id,
            ))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except errors.UniqueViolation as e:
            if conn:
                conn.rollback()
            raise ValueError("Ya existe un registro de inscripción para ese estudiante y actividad.") from e
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar inscripción: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def eliminar(self, inscripcion_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE inscripcion SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (inscripcion_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar inscripción: {e}")
            raise
        finally:
            if conn:
                conn.close()
