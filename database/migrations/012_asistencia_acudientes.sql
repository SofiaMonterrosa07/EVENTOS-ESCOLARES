-- Permite que los acudientes consulten asistencia de sus estudiantes vinculados.
UPDATE modulo_rol mr
SET estado = TRUE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) IN ('acudiente', 'padre o acudiente')
  AND LOWER(TRIM(m.nombre)) = 'asistencia'
  AND r.estado IS TRUE
  AND m.estado IS TRUE;

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE LOWER(TRIM(r.nombre)) IN ('acudiente', 'padre o acudiente')
  AND LOWER(TRIM(m.nombre)) = 'asistencia'
  AND r.estado IS TRUE
  AND m.estado IS TRUE
  AND NOT EXISTS (
      SELECT 1 FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );
