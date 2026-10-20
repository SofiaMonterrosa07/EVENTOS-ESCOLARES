from app.core.database import Database
from app.models.actividad_docente import ActividadDocente

class ActividadDocenteRepository:
    def __init__(self):
        self.db = Database()

    def obtener_docentes_disponibles(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.nombre, r.nombre AS rol_nombre
                FROM usuario u
                JOIN rol r ON r.id = u.rol_id
                WHERE u.estado IS TRUE AND r.estado IS TRUE
                  AND LOWER(TRIM(r.nombre)) IN ('docente', 'profesor', 'entrenador')
                ORDER BY u.nombre ASC;
            """)
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def _validar_docente(self, cursor, docente_id: int):
        cursor.execute("""
            SELECT 1
            FROM usuario u
            JOIN rol r ON r.id = u.rol_id
            WHERE u.id = %s AND u.estado IS TRUE AND r.estado IS TRUE
              AND LOWER(TRIM(r.nombre)) IN ('docente', 'profesor', 'entrenador')
            LIMIT 1;
        """, (docente_id,))
        if cursor.fetchone() is None:
            raise ValueError("Selecciona una cuenta docente activa.")

    def _validar_actividad_activa(self, cursor, actividad_id: int):
        cursor.execute("""
            SELECT 1 FROM actividad
            WHERE id = %s AND estado IS TRUE
            LIMIT 1;
        """, (actividad_id,))
        if cursor.fetchone() is None:
            raise ValueError("Selecciona una actividad activa.")

    # ============================================
    # FUNCIÓN AUXILIAR: VALIDAR CONFLICTO DE HORARIO
    # ============================================
    def verificar_conflicto_horario(self, docente_id: int, actividad_id: int, excluir_id: int = None):
        """
        Verifica si el docente ya tiene una actividad a la misma fecha y hora.
        Si se pasa excluir_id, ignora esa asignación (para actualizaciones).
        Retorna True si hay conflicto, False si está libre.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 1. Obtener fecha y hora de la nueva actividad
            cursor.execute("SELECT fecha, hora FROM actividad WHERE id = %s;", (actividad_id,))
            nueva_actividad = cursor.fetchone()

            if not nueva_actividad:
                return False  # La actividad no existe

            nueva_fecha = nueva_actividad['fecha']
            nueva_hora = nueva_actividad['hora']

            # 2. Verificar si el docente tiene otra actividad a la misma fecha y hora
            query = """
                SELECT COUNT(*) as total
                FROM actividad_docente ad
                JOIN actividad a ON ad.actividad_id = a.id
                WHERE ad.docente_id = %s AND ad.estado IS TRUE
                AND a.estado IS TRUE
                AND a.fecha = %s
                AND a.hora = %s
            """
            params = [docente_id, nueva_fecha, nueva_hora]

            # Si estamos actualizando, excluir la propia asignación
            if excluir_id is not None:
                query += " AND ad.id != %s"
                params.append(excluir_id)

            cursor.execute(query, tuple(params))
            resultado = cursor.fetchone()

            return resultado['total'] > 0  # True si hay conflicto
        except Exception as e:
            print(f"❌ Error al verificar conflicto de horario: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 1. OBTENER TODAS LAS ASIGNACIONES
    # ============================================
    def obtener_todos(self):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ad.*, 
                    u.nombre as docente_nombre, 
                    a.nombre as actividad_nombre,
                    a.fecha,
                    a.hora
                FROM actividad_docente ad
                JOIN usuario u ON ad.docente_id = u.id
                JOIN actividad a ON ad.actividad_id = a.id
                ORDER BY ad.id ASC;
            """)
            resultados = cursor.fetchall()
            return resultados
        except Exception as e:
            print(f"❌ Error al obtener asignaciones: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 2. OBTENER UNA ASIGNACIÓN POR ID
    # ============================================
    def obtener_por_id(self, id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ad.*, 
                    u.nombre as docente_nombre, 
                    a.nombre as actividad_nombre,
                    a.fecha,
                    a.hora
                FROM actividad_docente ad
                JOIN usuario u ON ad.docente_id = u.id
                JOIN actividad a ON ad.actividad_id = a.id
                WHERE ad.id = %s;
            """, (id,))
            resultado = cursor.fetchone()
            return resultado
        except Exception as e:
            print(f"❌ Error al obtener asignación: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 3. OBTENER DOCENTES DE UNA ACTIVIDAD
    # ============================================
    def obtener_por_actividad(self, actividad_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.id, 
                    u.nombre, 
                    ad.rol_en_actividad,
                    ad.id as asignacion_id,
                    ad.estado,
                    ad.creado,
                    ad.actualizado
                FROM actividad_docente ad
                JOIN usuario u ON ad.docente_id = u.id
                WHERE ad.actividad_id = %s;
            """, (actividad_id,))
            resultados = cursor.fetchall()
            return resultados
        except Exception as e:
            print(f"❌ Error al obtener docentes de la actividad: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def pertenece_a_docente_y_actividad(self, actividad_id: int, docente_id: int) -> bool:
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1
                FROM actividad_docente
                WHERE actividad_id = %s AND docente_id = %s AND estado IS TRUE
                LIMIT 1;
            """, (actividad_id, docente_id))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error al validar la asignacion docente-actividad: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 4. OBTENER ACTIVIDADES DE UN DOCENTE
    # ============================================
    def obtener_por_docente(self, docente_id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    a.id,
                    a.nombre,
                    a.fecha,
                    a.hora,
                    a.lugar,
                    ad.rol_en_actividad,
                    ad.id as asignacion_id,
                    ad.estado,
                    ad.creado,
                    ad.actualizado
                FROM actividad_docente ad
                JOIN actividad a ON ad.actividad_id = a.id
                WHERE ad.docente_id = %s AND ad.estado IS TRUE
                ORDER BY a.fecha, a.hora;
            """, (docente_id,))
            resultados = cursor.fetchall()
            return resultados
        except Exception as e:
            print(f"❌ Error al obtener actividades del docente: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 5. CREAR ASIGNACIÓN (CON VALIDACIÓN)
    # ============================================
    def crear(self, data: ActividadDocente):
        conn = None
        try:
            # Validar conflicto de horario
            if self.verificar_conflicto_horario(data.docente_id, data.actividad_id):
                raise ValueError("El docente ya tiene una actividad asignada a la misma fecha y hora.")

            conn = self.db.get_connection()
            cursor = conn.cursor()
            self._validar_docente(cursor, data.docente_id)
            self._validar_actividad_activa(cursor, data.actividad_id)
            query = """
                INSERT INTO actividad_docente (actividad_id, docente_id, rol_en_actividad, estado) 
                VALUES (%s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(query, (
                data.actividad_id,
                data.docente_id,
                data.rol_en_actividad, data.estado
            ))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
            return nuevo_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al crear asignación: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 6. ACTUALIZAR ASIGNACIÓN (CON VALIDACIÓN)
    # ============================================
    def actualizar(self, id: int, data: ActividadDocente):
        conn = None
        try:
            # Validar conflicto de horario (excluyendo la propia asignación)
            if data.estado and self.verificar_conflicto_horario(data.docente_id, data.actividad_id, excluir_id=id):
                raise ValueError("El docente ya tiene una actividad asignada a la misma fecha y hora.")

            conn = self.db.get_connection()
            cursor = conn.cursor()
            if data.estado:
                self._validar_docente(cursor, data.docente_id)
                self._validar_actividad_activa(cursor, data.actividad_id)
            query = """
                UPDATE actividad_docente 
                SET actividad_id = %s, docente_id = %s, rol_en_actividad = %s, estado = %s
                WHERE id = %s
                RETURNING id;
            """
            cursor.execute(query, (
                data.actividad_id,
                data.docente_id,
                data.rol_en_actividad,
                data.estado,
                id
            ))
            actualizado = cursor.fetchone()
            conn.commit()
            return actualizado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al actualizar asignación: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 7. ELIMINAR ASIGNACIÓN
    # ============================================
    def eliminar(self, id: int):
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE actividad_docente SET estado = FALSE, actualizado = CURRENT_TIMESTAMP WHERE id = %s AND estado IS TRUE RETURNING id;", (id,))
            eliminado = cursor.fetchone()
            conn.commit()
            return eliminado is not None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error al eliminar asignación: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ============================================
    # 8. VERIFICAR DISPONIBILIDAD (PARA CONSULTAS)
    # ============================================
    def verificar_disponibilidad(self, docente_id: int, fecha: str, hora: str):
        """
        Verifica si un docente está disponible en una fecha y hora específicas.
        Retorna True si está disponible, False si tiene conflicto.
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM actividad_docente ad
                JOIN actividad a ON ad.actividad_id = a.id
                WHERE ad.docente_id = %s
                AND ad.estado IS TRUE AND a.estado IS TRUE
                AND a.fecha = %s
                AND a.hora = %s
            """, (docente_id, fecha, hora))
            resultado = cursor.fetchone()
            return resultado['total'] == 0
        except Exception as e:
            print(f"❌ Error al verificar disponibilidad: {e}")
            raise
        finally:
            if conn:
                conn.close()
