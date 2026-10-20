from datetime import date
from app.core.database import Database
from app.models.actividad import Actividad


class ActividadRepository:

    def __init__(self):
        self.db = Database()

    def _validar_categoria_activa(self, cursor, categoria_id: int):
        cursor.execute("""
            SELECT 1 FROM categoria_actividad
            WHERE id = %s AND estado IS TRUE
            LIMIT 1;
        """, (categoria_id,))
        if cursor.fetchone() is None:
            raise ValueError("Selecciona una categoría activa.")

    def _validar_capacidad(self, cursor, actividad_id: int, cupo: int) -> bool:
        cursor.execute("SELECT id FROM actividad WHERE id = %s FOR UPDATE;", (actividad_id,))
        if cursor.fetchone() is None:
            return False
        cursor.execute("""
            SELECT COUNT(*)::integer AS cantidad
            FROM inscripcion i
            JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
            JOIN usuario u ON u.id = e.usuario_id AND u.estado IS TRUE
            WHERE i.actividad_id = %s AND i.estado IS TRUE;
        """, (actividad_id,))
        inscritos = int(cursor.fetchone()["cantidad"])
        if int(cupo) < inscritos:
            raise ValueError("El cupo no puede ser menor que las inscripciones activas.")
        return True

    # ==========================================
    # OBTENER TODAS LAS ACTIVIDADES
    # ==========================================

    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*,
                       COALESCE((
                           SELECT STRING_AGG(DISTINCT u.nombre, ', ' ORDER BY u.nombre)
                           FROM actividad_docente ad
                           JOIN usuario u ON u.id = ad.docente_id AND u.estado IS TRUE
                           WHERE ad.actividad_id = a.id AND ad.estado IS TRUE
                       ), 'Sin docente asignado') AS docentes_asignados,
                       (
                           SELECT COUNT(DISTINCT i.estudiante_id)::integer
                           FROM inscripcion i
                           JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                           JOIN usuario eu ON eu.id = e.usuario_id AND eu.estado IS TRUE
                           WHERE i.actividad_id = a.id AND i.estado IS TRUE
                       ) AS cantidad_inscritos
                FROM actividad a
                ORDER BY a.id ASC;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Error al obtener actividades: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_asociaciones(self, actividad_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM actividad WHERE id = %s;", (actividad_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute("""
                SELECT DISTINCT docente_id
                FROM actividad_docente
                WHERE actividad_id = %s AND estado IS TRUE
                ORDER BY docente_id;
            """, (actividad_id,))
            docentes = [fila["docente_id"] for fila in cursor.fetchall()]
            cursor.execute("""
                SELECT DISTINCT i.estudiante_id
                FROM inscripcion i
                JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                JOIN usuario u ON u.id = e.usuario_id AND u.estado IS TRUE
                WHERE i.actividad_id = %s AND i.estado IS TRUE
                ORDER BY i.estudiante_id;
            """, (actividad_id,))
            estudiantes = [fila["estudiante_id"] for fila in cursor.fetchall()]
            return {"docente_ids": docentes, "estudiante_ids": estudiantes}
        finally:
            if conn:
                conn.close()

    def reemplazar_asociaciones(self, actividad_id: int, docente_ids: list[int], estudiante_ids: list[int]):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, fecha, hora, cupo, estado
                FROM actividad
                WHERE id = %s
                FOR UPDATE;
            """, (actividad_id,))
            actividad = cursor.fetchone()
            if actividad is None:
                raise ValueError("No se encontro la actividad.")
            if len(docente_ids) != len(set(docente_ids)) or len(estudiante_ids) != len(set(estudiante_ids)):
                raise ValueError("No repitas docentes ni estudiantes.")

            if docente_ids:
                cursor.execute("""
                    SELECT u.id, u.nombre
                    FROM usuario u
                    JOIN rol r ON r.id = u.rol_id
                    WHERE u.id = ANY(%s) AND u.estado IS TRUE AND r.estado IS TRUE
                      AND LOWER(TRIM(r.nombre)) IN ('docente', 'profesor', 'entrenador');
                """, (docente_ids,))
                docentes_validos = {fila["id"] for fila in cursor.fetchall()}
                if docentes_validos != set(docente_ids):
                    raise ValueError("Selecciona unicamente docentes activos.")
                cursor.execute("""
                    SELECT DISTINCT u.nombre
                    FROM actividad_docente ad
                    JOIN actividad otra ON otra.id = ad.actividad_id AND otra.estado IS TRUE
                    JOIN usuario u ON u.id = ad.docente_id
                    WHERE ad.docente_id = ANY(%s) AND ad.estado IS TRUE
                      AND ad.actividad_id <> %s
                      AND otra.fecha = %s AND otra.hora = %s;
                """, (docente_ids, actividad_id, actividad["fecha"], actividad["hora"]))
                conflictos = [fila["nombre"] for fila in cursor.fetchall()]
                if conflictos:
                    raise ValueError("Conflicto de horario para: " + ", ".join(conflictos))

            if estudiante_ids:
                cursor.execute("""
                    SELECT e.id
                    FROM estudiante e
                    JOIN usuario u ON u.id = e.usuario_id
                    WHERE e.id = ANY(%s) AND e.estado IS TRUE AND u.estado IS TRUE;
                """, (estudiante_ids,))
                estudiantes_validos = {fila["id"] for fila in cursor.fetchall()}
                if estudiantes_validos != set(estudiante_ids):
                    raise ValueError("Selecciona unicamente estudiantes activos.")
            if len(estudiante_ids) > int(actividad["cupo"]):
                raise ValueError("La cantidad de estudiantes supera el cupo de la actividad.")

            cursor.execute("""
                SELECT DISTINCT estudiante_id
                FROM inscripcion
                WHERE actividad_id = %s AND estado IS TRUE;
            """, (actividad_id,))
            inscritos_actuales = {fila["estudiante_id"] for fila in cursor.fetchall()}
            nuevos_inscritos = set(estudiante_ids) - inscritos_actuales
            if nuevos_inscritos and (not actividad["estado"] or actividad["fecha"] < date.today()):
                raise ValueError("Solo puedes inscribir estudiantes a una actividad activa y vigente.")

            cursor.execute("""
                SELECT id, docente_id
                FROM actividad_docente
                WHERE actividad_id = %s;
            """, (actividad_id,))
            asignaciones = cursor.fetchall()
            docentes_existentes = set()
            for asignacion in asignaciones:
                docentes_existentes.add(asignacion["docente_id"])
                cursor.execute("""
                    UPDATE actividad_docente
                    SET estado = %s, actualizado = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (asignacion["docente_id"] in docente_ids, asignacion["id"]))
            for docente_id in docente_ids:
                if docente_id not in docentes_existentes:
                    cursor.execute("""
                        INSERT INTO actividad_docente (actividad_id, docente_id, rol_en_actividad, estado)
                        VALUES (%s, %s, %s, TRUE);
                    """, (actividad_id, docente_id, "Acompañante"))

            cursor.execute("""
                SELECT id, estudiante_id
                FROM inscripcion
                WHERE actividad_id = %s;
            """, (actividad_id,))
            inscripciones = cursor.fetchall()
            estudiantes_existentes = set()
            for inscripcion in inscripciones:
                estudiantes_existentes.add(inscripcion["estudiante_id"])
                cursor.execute("""
                    UPDATE inscripcion
                    SET estado = %s, actualizado = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (inscripcion["estudiante_id"] in estudiante_ids, inscripcion["id"]))
            for estudiante_id in estudiante_ids:
                if estudiante_id not in estudiantes_existentes:
                    cursor.execute("""
                        INSERT INTO inscripcion (estudiante_id, actividad_id, fecha_inscripcion, estado)
                        VALUES (%s, %s, CURRENT_DATE, TRUE);
                    """, (estudiante_id, actividad_id))

            conn.commit()
            return {"docentes": len(docente_ids), "estudiantes": len(estudiante_ids)}
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def obtener_publicas(self):
        """Catalogo visible para estudiantes y acudientes: actividades vigentes y futuras."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM actividad
                WHERE estado IS TRUE AND fecha >= CURRENT_DATE
                ORDER BY fecha, hora;
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener actividades publicas: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_docente(self, usuario_id: int):
        """Devuelve el catálogo asignado al docente autenticado."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT a.*
                FROM actividad a
                JOIN actividad_docente ad ON ad.actividad_id = a.id AND ad.estado IS TRUE
                WHERE ad.docente_id = %s
                ORDER BY a.fecha, a.hora;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener las actividades asignadas al docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def obtener_por_acudiente(self, usuario_id: int):
        """Devuelve solo actividades con inscripciones activas de sus acudidos."""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT a.*
                FROM actividad a
                JOIN inscripcion i ON i.actividad_id = a.id AND i.estado IS TRUE
                JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                JOIN usuario estudiante_usuario ON estudiante_usuario.id = e.usuario_id AND estudiante_usuario.estado IS TRUE
                JOIN acudiente_estudiante ae ON ae.estudiante_id = e.id
                JOIN acudiente ac ON ac.id = ae.acudiente_id AND ac.estado IS TRUE
                WHERE ac.usuario_id = %s
                ORDER BY a.fecha, a.hora, a.id;
            """, (usuario_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener actividades de los acudidos: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_acudido(self, actividad_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM inscripcion i
                JOIN estudiante e ON e.id = i.estudiante_id AND e.estado IS TRUE
                JOIN acudiente_estudiante ae ON ae.estudiante_id = e.id
                JOIN acudiente ac ON ac.id = ae.acudiente_id AND ac.estado IS TRUE
                WHERE i.actividad_id = %s AND i.estado IS TRUE AND ac.usuario_id = %s
                LIMIT 1;
            """, (actividad_id, usuario_id))
            return cursor.fetchone() is not None
        finally:
            if conn:
                conn.close()

    def es_publica(self, actividad_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM actividad
                WHERE id = %s AND estado IS TRUE AND fecha >= CURRENT_DATE
                LIMIT 1;
            """, (actividad_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar la actividad publica: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_docente(self, actividad_id: int, usuario_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM actividad_docente
                WHERE actividad_id = %s AND docente_id = %s AND estado IS TRUE
                LIMIT 1;
            """, (actividad_id, usuario_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar la asignacion del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ==========================================
    # OBTENER ACTIVIDAD POR ID
    # ==========================================

    def obtener_por_id(self, actividad_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM actividad
                WHERE id = %s;
            """, (actividad_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"❌ Error al obtener actividad: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ==========================================
    # CREAR ACTIVIDAD
    # ==========================================

    def crear(self, actividad: Actividad):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            self._validar_categoria_activa(cursor, actividad.categoria_id)
            cursor.execute("""
                INSERT INTO actividad
                (
                    nombre,
                    descripcion,
                    fecha,
                    hora,
                    lugar,
                    cupo,
                    categoria_id,
                    estado
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                actividad.nombre,
                actividad.descripcion,
                actividad.fecha,
                actividad.hora,
                actividad.lugar,
                actividad.cupo,
                actividad.categoria_id,
                actividad.estado
            ))
            row = cursor.fetchone()
            if row is None:
                raise ValueError("No se obtuvo el ID de la actividad creada.")
            nuevo_id = row[0]
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear actividad: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ==========================================
    # ACTUALIZAR ACTIVIDAD
    # ==========================================

    def actualizar(self, actividad_id: int, actividad: Actividad):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            if not self._validar_capacidad(cursor, actividad_id, actividad.cupo):
                conn.rollback()
                return False
            self._validar_categoria_activa(cursor, actividad.categoria_id)
            cursor.execute("""
                UPDATE actividad
                SET
                    nombre = %s,
                    descripcion = %s,
                    fecha = %s,
                    hora = %s,
                    lugar = %s,
                    cupo = %s,
                    categoria_id = %s,
                    estado = %s
                WHERE id = %s
                RETURNING id;
            """, (
                actividad.nombre,
                actividad.descripcion,
                actividad.fecha,
                actividad.hora,
                actividad.lugar,
                actividad.cupo,
                actividad.categoria_id,
                actividad.estado,
                actividad_id
            ))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar actividad: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ==========================================
    # ELIMINAR ACTIVIDAD
    # ==========================================

    def eliminar(self, actividad_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE actividad SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;
            """, (actividad_id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar actividad: {e}")
            raise
        finally:
            if conn:
                conn.close()
