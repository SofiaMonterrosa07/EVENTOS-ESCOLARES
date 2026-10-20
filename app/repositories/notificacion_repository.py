from app.core.database import Database
from app.models.notificacion import NotificacionCreate


class NotificacionRepository:
	def __init__(self):
		self.db = Database()

	def obtener_por_usuario(self, usuario_id: int):
		conn = None
		try:
			conn = self.db.get_connection()
			cursor = conn.cursor()
			cursor.execute("""
				SELECT n.id, n.usuario_id, n.creador_usuario_id, n.titulo,
				       n.mensaje, n.fecha_envio, n.leida, n.actividad_id,
				       a.nombre AS actividad_nombre, n.estado
			FROM notificacion n
			LEFT JOIN actividad a ON a.id = n.actividad_id
			WHERE n.estado IS TRUE
			  AND (n.usuario_id = %s OR n.creador_usuario_id = %s)
			ORDER BY n.fecha_envio DESC, n.id DESC;
			""", (usuario_id, usuario_id))
			return cursor.fetchall()
		finally:
			if conn:
				conn.close()

	def obtener_por_id(self, notificacion_id: int, usuario_id: int):
		conn = None
		try:
			conn = self.db.get_connection()
			cursor = conn.cursor()
			cursor.execute("""
				SELECT n.id, n.usuario_id, n.creador_usuario_id, n.titulo,
				       n.mensaje, n.fecha_envio, n.leida, n.actividad_id,
				       a.nombre AS actividad_nombre, n.estado
			FROM notificacion n
			LEFT JOIN actividad a ON a.id = n.actividad_id
			WHERE n.id = %s AND n.estado IS TRUE
			  AND (n.usuario_id = %s OR n.creador_usuario_id = %s)
			LIMIT 1;
			""", (notificacion_id, usuario_id, usuario_id))
			return cursor.fetchone()
		finally:
			if conn:
				conn.close()

	def crear(self, notificacion: NotificacionCreate, creador_usuario_id: int):
		conn = None
		try:
			conn = self.db.get_connection()
			cursor = conn.cursor()
			cursor.execute("""
				SELECT 1 FROM usuario WHERE id = %s AND estado IS TRUE LIMIT 1;
			""", (notificacion.usuario_id,))
			if cursor.fetchone() is None:
				raise ValueError("Selecciona una cuenta activa como destinataria.")
			if notificacion.actividad_id is not None:
				cursor.execute("""
					SELECT 1 FROM actividad WHERE id = %s AND estado IS TRUE LIMIT 1;
				""", (notificacion.actividad_id,))
				if cursor.fetchone() is None:
					raise ValueError("La actividad asociada no existe o está inactiva.")
			cursor.execute("""
				INSERT INTO notificacion
					(usuario_id, creador_usuario_id, titulo, mensaje, actividad_id, leida, estado)
				VALUES (%s, %s, %s, %s, %s, FALSE, TRUE)
				RETURNING id;
			""", (
				notificacion.usuario_id, creador_usuario_id, notificacion.titulo.strip(),
				notificacion.mensaje.strip(), notificacion.actividad_id,
			))
			nuevo_id = int(cursor.fetchone()["id"])
			conn.commit()
			return nuevo_id
		except Exception:
			if conn:
				conn.rollback()
			raise
		finally:
			if conn:
				conn.close()

	def marcar_leida(self, notificacion_id: int, usuario_id: int) -> bool:
		conn = None
		try:
			conn = self.db.get_connection()
			cursor = conn.cursor()
			cursor.execute("""
				UPDATE notificacion
				SET leida = TRUE, actualizado = CURRENT_TIMESTAMP
				WHERE id = %s AND usuario_id = %s AND estado IS TRUE
				RETURNING id;
			""", (notificacion_id, usuario_id))
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
