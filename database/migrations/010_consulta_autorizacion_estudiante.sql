-- Habilita al estudiante para consultar el estado de sus propias autorizaciones.
-- La API filtra por la identidad de sesión y mantiene la respuesta reservada al acudiente.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM rol WHERE LOWER(TRIM(nombre)) = 'estudiante' AND estado IS TRUE
    ) THEN
        RAISE EXCEPTION 'No existe un rol Estudiante activo; revise los permisos antes de continuar.';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM modulo WHERE LOWER(TRIM(nombre)) = 'autorizaciones' AND estado IS TRUE
    ) THEN
        RAISE EXCEPTION 'El módulo Autorizaciones no está activo; revise los permisos antes de continuar.';
    END IF;
END;
$$;

UPDATE modulo_rol mr
SET estado = TRUE, actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'estudiante'
  AND LOWER(TRIM(m.nombre)) = 'autorizaciones'
  AND mr.estado IS DISTINCT FROM TRUE;

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE r.estado IS TRUE
  AND m.estado IS TRUE
  AND LOWER(TRIM(r.nombre)) = 'estudiante'
  AND LOWER(TRIM(m.nombre)) = 'autorizaciones'
  AND NOT EXISTS (
      SELECT 1 FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );
