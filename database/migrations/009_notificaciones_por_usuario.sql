-- Habilita el módulo ya existente y permite que los roles activos consulten
-- y marquen como leídas únicamente sus notificaciones. No crea ni borra filas.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM modulo WHERE LOWER(TRIM(nombre)) = 'notificaciones'
    ) THEN
        RAISE EXCEPTION 'No existe el módulo Notificaciones; revise el esquema antes de continuar.';
    END IF;
END;
$$;

UPDATE modulo
SET estado = TRUE, actualizado = statement_timestamp()
WHERE LOWER(TRIM(nombre)) = 'notificaciones'
  AND estado IS DISTINCT FROM TRUE;

UPDATE modulo_rol mr
SET estado = TRUE, actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND r.estado IS TRUE
  AND LOWER(TRIM(m.nombre)) = 'notificaciones'
  AND mr.estado IS DISTINCT FROM TRUE;

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE r.estado IS TRUE
  AND m.estado IS TRUE
  AND LOWER(TRIM(m.nombre)) = 'notificaciones'
  AND NOT EXISTS (
      SELECT 1 FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );
